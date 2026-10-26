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

// Since slice 064 v2 the chart opens on the top seat and one layer (I2).
// Checks about the whole tree open the two middle seats first.
const ALL_OPEN = { "P-Sector34": true, "P-Ambala": true };

/* ── 1. every seat is drawn, exactly once ───────────────────────────────── */
{
  const out = render(ROWS, {}, {}, ALL_OPEN);
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
  const out = render(ROWS, {}, {}, ALL_OPEN);
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

/* ── 4. a filter shows the matches and the seats above them, faded ──────── */
// Surbhi, 23 Oct 2026 (OP-4): this REPLACES the 15 Oct rule "a filter greys,
// it does not hide". Only the matches and every seat above them are drawn;
// the ones above are faded; the path to each match is open.
{
  const out = render(ROWS, { "pos-f-open": "open" });
  ok("a match is drawn, even below the first layer (its path is open)", out.html.includes(">Cashier<"));
  ok("and every seat above it, up to the top",
     out.html.includes(">Store Manager<") && out.html.includes(">Director<"));
  ["Counter Staff", "Store Manager Ambala", "Housekeeping", "Area Manager"].forEach((t) => {
    ok("a seat that is not a match and has none below it is left out",
       !out.html.includes(">" + t + "<"), t + " is still drawn");
  });
  const fadedBefore = (name) => {
    const at = out.html.indexOf(">" + name + "<");
    const node = out.html.lastIndexOf('<div class="oc-node', at);
    return out.html.slice(node, at).includes("opacity:.45");
  };
  ok("the seats above the match are faded", fadedBefore("Director") && fadedBefore("Store Manager"));
  ok("the match itself is not faded", !fadedBefore("Cashier"));
  ok("a line says how many match, with Clear filter",
     out.html.includes("1 matching") && out.html.includes("posClearFilter()"));
  // The count used to be grey text counting the WHOLE company whatever the
  // filter said. It is three tiles now, computed over the filtered rows.
  ok("the tiles are drawn", /oc-stat|pf-card/.test(out.tiles),
     "tiles read: " + out.tiles.slice(0, 80));
  ok("the filter rule is explained on screen", out.note !== "none");
  const br = render(ROWS, { "pos-f-arrange": "branch" }, {}, { "br:Ambala": true });
  ok("a manager in another branch, or filtered out, is not \"above your view\"",
     out.html.split("reports above your view").length - 1 === 0
     && br.html.split("reports above your view").length - 1 === 0);
  const none = render(ROWS, { "pos-f-role": "Nobody Has This" });
  ok("no match says so, with the way back",
     none.html.includes("Nothing matches.") && none.html.includes("Clear the filter"));
}

/* ── 4b. a filter picks its view, and Clear filter puts the old one back ── */
{
  for (const [sel, val, arr, want] of [["pos-f-branch", "Ambala", "branch", "branch"],
                                       ["pos-f-dept", "Sales", "department", "department"],
                                       ["pos-f-role", "Clerk", "reporting", "reporting"],
                                       ["pos-f-open", "open", "", "department"]]) {
    const ctx = makeContext({ "pos-f-view": "list", "pos-f-arrange": "department" });
    ctx.POS.rows = ROWS.map((r) => Object.assign({}, r, { designation: r.id === "P-Cashier" ? "Clerk" : "" }));
    ctx.POS.collapsed = { "P-Ambala": true };
    ctx.POS.expanded = {};
    ctx.__els[sel].value = val;
    ctx.posFilterChanged(arr);
    ok(sel + " moves the list to the chart", ctx.__els["pos-f-view"].value === "tree");
    ok(sel + " arranges " + want, ctx.__els["pos-f-arrange"].value === want,
       "got " + ctx.__els["pos-f-arrange"].value);
    ctx.posClearFilter();
    ok(sel + ": Clear filter empties the filter", ctx.__els[sel].value === "");
    ok(sel + ": and puts back the view, the arrangement and the folds",
       ctx.__els["pos-f-view"].value === "list" && ctx.__els["pos-f-arrange"].value === "department"
       && ctx.POS.collapsed["P-Ambala"] === true);
  }
}

/* ── 4c. it opens on the top seat and one layer; one press opens a box ──── */
{
  const out = render(ROWS);
  ok("the first layer is drawn", out.html.includes(">Store Manager<"));
  ok("the layer below it is folded", !out.html.includes(">Cashier<"));
  const ctx = makeContext({ "pos-f-view": "tree", "pos-f-arrange": "branch" });
  ctx.POS.rows = ROWS; ctx.POS.collapsed = {}; ctx.POS.expanded = {};
  ctx.posPaint();
  ok("a branch starts closed", !ctx.__els["pos-body"].innerHTML.includes(">Housekeeping<"));
  ctx.posToggle("br:Ambala");
  ok("ONE press opens a closed branch (the live bug: it took two)",
     ctx.__els["pos-body"].innerHTML.includes(">Store Manager Ambala<"));
  ctx.posToggle("br:Ambala");
  ok("and the next press closes it", !ctx.__els["pos-body"].innerHTML.includes(">Store Manager Ambala<"));
  const c2 = makeContext({ "pos-f-view": "tree" });
  c2.POS.rows = ROWS; c2.POS.collapsed = {}; c2.POS.expanded = {};
  c2.posPaint();
  c2.posToggle("P-Sector34");
  ok("one press opens a folded seat", c2.__els["pos-body"].innerHTML.includes(">Cashier<"));
  c2.posToggle("P-Director");
  ok("one press closes an open seat", !c2.__els["pos-body"].innerHTML.includes(">Store Manager<"));
}

/* ── 4d. three or more seats with nobody under them hang in one column ──── */
{
  const fam = [seat("P-M", "Manager", ""), seat("P-L", "Lead", "P-M")];
  ["A", "B", "C"].forEach((x) => fam.push(seat("P-" + x, "Seat " + x, "P-M")));
  fam.push(seat("P-LR", "Lead Report", "P-L"));
  const out = render(fam);
  ok("the childless seats hang under the leads",
     out.html.includes('class="oc-fam"') && out.html.includes('class="oc-hang under"'));
  ok("each of them in its own hanging item", out.html.split('class="oc-hang-item"').length - 1 === 3);
  ok("the lead stays in the row", out.html.indexOf(">Lead<") < out.html.indexOf('class="oc-hang under"'));
  const two = render([seat("P-M", "Manager", ""), seat("P-A", "Seat A", "P-M"), seat("P-B", "Seat B", "P-M")]);
  ok("one or two stay in the row", !two.html.includes("oc-hang"));
  const flat = render([seat("P-M", "Manager", "")].concat(["A", "B", "C"].map((x) => seat("P-" + x, "Seat " + x, "P-M"))));
  ok("with no leads the column hangs straight under the manager",
     flat.html.includes("oc-hang-slot") && !flat.html.includes("oc-fam"));
}

/* ── 4e. the Organisation chart is not changed by any of this ───────────── */
{
  const ctx = makeContext({});
  const n = { id: "E1", title: "Boss", people: [],
              children: ["A", "B", "C"].map((x) => ({ id: x, title: x, people: [], children: [] })) };
  ok("without the Positions option a family stays one row", !ctx.ocRender(n, true).includes("oc-hang"));
}

/* ── 4f. zoom, the tools, print, No reporting manager ───────────────────── */
{
  const out = render(ROWS);
  ok("the chart sits in ONE zoom wrapper inside its scroll box",
     out.html.split('class="oc-zoom"').length - 1 === 1
     && out.html.indexOf('class="oc-tree"') < out.html.indexOf('class="oc-zoom"'));
  ok("it opens at 100 %", out.html.includes('style="zoom:1"') && out.html.includes(">100%<"));
  ["posZoom(-1)", "posZoom(1)", "posZoom(0)", "posZoomFit()"].forEach((f) =>
    ok("the tools offer " + f, out.html.includes(f)));
  // Slice 069 (D-2, SEC-3): the old Print button is gone - it printed flags,
  // leaving dates and the HR box. The wall chart panel is the way to print.
  ok("the zoom row has no Print button", !out.html.includes("window.print()") && !/>Print</.test(out.html));
  ok("the zoom row is labelled Zoom", out.html.includes('role="group" aria-label="Zoom"'));
  ok("the tools are left out of print", out.html.includes('class="pos-ztools noprint"'));
  ok("a print-only header says what is printed",
     out.html.includes('class="pos-printhead"') && out.html.includes("Reporting lines") && out.html.includes("No filter"));
  const ctx = makeContext({ "pos-f-view": "tree" });
  ctx.POS.rows = ROWS; ctx.POS.collapsed = {}; ctx.POS.expanded = {};
  ctx.posZoom(1);   // no chart in this DOM: must not throw
  ok("zoom limits are 40 % and 200 %", ctx.POS_ZMIN === 0.4 && ctx.POS_ZMAX === 2);
  const src = fs.readFileSync(PORTAL, "utf8");
  ok("zoom is never stored", !/localStorage[^\n]*zoom|zoom[^\n]*localStorage/i.test(src));
  const css = fs.readFileSync(path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "public",
                                        "css", "ess", "panels.css"), "utf8");
  ok("print: A4 landscape", /@page\{size:A4 landscape/.test(css));
  ok("print: anything private never prints", /\.private,\[data-private\]\{display:none !important\}/.test(css));
  ok("print (069 SEC-3): flags, tags and the HR box never print",
     ["#panel-positions .oc-flag", "#panel-positions .oc-tag", ".pos-nomgr-row,"].every((x) => css.includes(x)));
  const pr = makeContext({ "pos-f-view": "tree" });
  pr.__els["sb-name"] = { textContent: "PRINTER-SNTL" };
  pr.__els["sb-desig"] = { textContent: "ROLE-SNTL" };
  pr.POS.rows = ROWS; pr.POS.collapsed = {}; pr.POS.expanded = {};
  pr.posPaint();
  const head = (pr.__els["pos-body"].innerHTML.match(/<div class="pos-printhead">[\s\S]*?<\/div>/) || [""])[0];
  ok("print header (069 AC-3a): never who printed it",
     head && !/PRINTER-SNTL|ROLE-SNTL|printed by/.test(head), head);
  // Review M1: "never printed" covers the list view too. Every flag note and
  // the Notice period column carry a class the print rule hides.
  ok("print (069 M1): the list's flag notes and Notice period column never print",
     ["#pos-body .pos-flag", "#pos-body .pos-leave-col"].every((x) => css.includes(x)));
  const li = makeContext({ "pos-f-view": "list" });
  li.POS.rows = [seat("P-L1", "Cashier", "", { key: true, status: "Frozen", leaving_on: "2026-11-30",
    people: [{ employee: "E", name: "Lata Leaver", weight: 50, covering: true, leaving: "2026-11-30" }] })];
  li.POS.collapsed = {}; li.POS.expanded = {};
  li.posPaint();
  const listHtml = li.__els["pos-body"].innerHTML;
  const printed = listHtml.replace(/<span class="pf-card-meta pos-flag">[^<]*<\/span>/g, "")
    .replace(/<t[dh] class="pos-leave-col">[\s\S]*?<\/t[dh]>/g, "");
  ok("list view: flags and leaving dates are drawn on screen", /key seat/.test(listHtml) && /leaving/.test(listHtml));
  ok("list view: what is left for print has no leaving date, key seat, Frozen, covering or %",
     !/leaving|key seat|Frozen|covering|50%|30 Nov/.test(printed) && /Lata Leaver/.test(printed), printed.slice(0, 300));
  ok("print header keeps the view, the date and the filter words",
     /Positions/.test(head) && /seats as at/.test(head) && /No filter/.test(head) && / on /.test(head));
  ok("print: trays, dialogs, tiles, filters and fold buttons are left out",
     ["#pos-tiles", "#pos-layer", ".gp-backdrop", "#panel-positions .oc-toggle", ".pos-ztools"].every((x) => css.includes(x)));
  const hr = makeContext({ "pos-f-view": "tree" });
  hr.POS.rows = ROWS.concat([seat("P-Loose2", "Loose", "")]);
  hr.POS.unseated = [{ no_manager: true }];
  hr.POS.collapsed = {}; hr.POS.expanded = {};
  hr.posPaint();
  const h = hr.__els["pos-body"].innerHTML;
  ok("HR see the No reporting manager box on the chart, opening its tray",
     h.includes("pos-nomgr") && h.includes("posNoMgrSheet()") && h.includes("2 people"));
  ok("nobody else does", !out.html.includes("pos-nomgr"));
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
  const out = render(ROWS, {}, {}, ALL_OPEN);
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
  const out = render(risky, {}, {}, { "P-S1": true });
  ok("the one with a team is drawn on its own",
     out.html.split('<span class="ti">Supervisor</span>').length - 1 === 2,
     "both Supervisors must be separate cards");
  ok("and its report is still under it", out.html.includes(">Their Report<"));
}

/* ── 13. a group a filter does not touch is left out (OP-4) ─────────────── */
{
  const mixed = [
    seat("P-Boss2", "Store Manager", "", { branch: "Noida" }),
    seat("P-A1", "Clerk", "P-Boss2", { branch: "Ambala" }),
    seat("P-A2", "Clerk", "P-Boss2", { branch: "Ambala" }),
  ];
  const out = render(mixed, { "pos-f-branch": "Noida" });
  ok("a group matching nothing is left out", !out.html.includes(">Clerk<"));
  ok("the match is drawn", out.html.includes(">Store Manager<"));
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
    {}, { "br:Ambala": true, "P-Top5": true });
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
    {}, { "br:Ambala": true, "P-SM": true });

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

/* ── 22. slice 071: names in the "In no seat" tray ──────────────────────── */
const UN = [
  { employee: "HR-EMP-00380", name: "Ravi Kumar", job_role: "Cashier", branch: "Sector 34", joined: "2026-09-17", no_manager: false },
  { employee: "HR-EMP-00381", name: "Anjali Saini", job_role: "Cashier", branch: "Sector 34", joined: "2025-03-14", no_manager: true },
  { employee: "HR-EMP-00382", name: "Ravi Kumar", job_role: "Counter", branch: "Sector 34", joined: "2026-10-01", no_manager: false },
  { employee: "HR-EMP-00383", name: "Bina Rao", job_role: "Driver", branch: "Ambala", joined: "2026-10-02", no_manager: false },
];
const UNROWS = ROWS.map((r) => (r.id === "P-Cashier" ? Object.assign({}, r, { designation: "Cashier" })
  : r.id === "P-Counter" ? Object.assign({}, r, { designation: "Counter" }) : r));
{
  const t = trayContext({ unseated: UN, rows: UNROWS, active: 40 });
  t.ctx.posUnseatedSheet();
  const h = t.layer();
  ok("071 rows: every person appears exactly once",
     UN.every((p) => h.split(">" + p.employee + "<").length === 2));
  ok("071 rows: the name links to the employee record in a new tab",
     h.includes('href="/app/employee/HR-EMP-00380">Ravi Kumar</a>') && h.includes('target="_blank" rel="noopener"'));
  ok("071 rows: the ID sits beside the name, in grey", h.includes('Ravi Kumar</a> <span class="su">HR-EMP-00380</span>'));
  ok("071 rows: joined this year has no year", h.includes("Joined 17 Sep<"));
  ok("071 rows: joined another year shows it", h.includes("Joined 14 Mar 2025"));
  ok("071 rows: No manager only when true",
     h.split("No manager</span>").length === 2 && /HR-EMP-00381<\/span><span class="pos-un-meta su">Joined 14 Mar 2025 <span class="pos-chip">No manager/.test(h));
  ok("071 rows: sorted by name within the role", h.indexOf("Anjali Saini") < h.indexOf("HR-EMP-00380"));
  ok("071 rows: the role line keeps its words", h.includes("2 Cashier · matching seat:") && h.includes("1 Driver · no matching seat"));
  t.ctx.POS.unseated = [];
  t.ctx.posUnseatedSheet();
  ok("071 empty: the empty sentence and 0 people",
     t.layer().includes("In no seat · 0 people") && t.layer().includes("Everybody active is in a seat now"));
}

/* 071 steps 3-4: buttons, and the confirm before a full seat. */
const UN2 = UN.concat([
  { employee: "HR-EMP-00384", name: "Chetan Lal", job_role: "Loader", branch: "Ambala", joined: "2026-10-03", no_manager: false },
  { employee: "HR-EMP-00385", name: "Deep Kaur", job_role: "Packer", branch: "Sector 34", joined: "2026-10-04", no_manager: false },
]);
const UNROWS2 = UNROWS.concat([
  seat("P-Loader", "Loader", "P-Ambala", { branch: "Ambala", designation: "Loader", seats: 0, filled: 2, open: 0 }),
  seat("P-PackA", "A Packer", "P-Sector34", { designation: "Packer", seats: 1, filled: 1, open: 0 }),
  seat("P-PackB", "B Packer", "P-Sector34", { designation: "Packer", seats: 2, filled: 1, open: 1 }),
]);
function unContext(mayEdit) {
  const t = trayContext({ unseated: UN2, rows: UNROWS2, active: 40, may_edit: mayEdit });
  const els = t.ctx.__els, calls = [];
  const box = (id, extra) => (els[id] = Object.assign({
    id, innerHTML: "", textContent: "", value: "", style: {}, checked: false, disabled: false,
    classList: (() => { const s = new Set(); return { add: (c) => s.add(c), remove: (c) => s.delete(c), contains: (c) => s.has(c) }; })(),
    focus() { t.focused.push(id); },
  }, extra || {}));
  ["pos-full", "pos-full-x", "pos-full-no", "pos-person", "pos-p-q", "pos-p-weight", "pos-p-type", "pos-p-until",
   "pos-p-delegate", "pos-p-holds", "pos-p-until-wrap", "pos-person-err", "pos-p-list", "pos-p-save", "pos-p-ctx"].forEach((id) => box(id));
  els["pos-p-list"].children = [];
  t.ctx.gpFetch = (method, args) => { calls.push([method, args]); return t.fetch ? t.fetch(method, args) : new Promise(() => {}); };
  t.calls = calls; t.box = box;
  return t;
}
function rowOf(h, emp) { return (h.split('<li class="pos-un-p">').filter((x) => x.includes(">" + emp + "<"))[0] || "").split("</li>")[0]; }
{
  const t = unContext(false);
  t.ctx.posUnseatedSheet();
  const h = t.layer();
  ok("071 HR User: names but no buttons and no full words",
     h.includes("Ravi Kumar") && !h.includes("Place in seat") && !h.includes("Place anyway") && !h.includes("This seat is full"));
}
{
  const t = unContext(true);
  t.ctx.posUnseatedSheet();
  const h = t.layer();
  ok("071 room: Place in seat", rowOf(h, "HR-EMP-00381").includes(">Place in seat</button>") && !rowOf(h, "HR-EMP-00381").includes("full"));
  ok("071 full: the words, then Place anyway",
     /This seat is full<\/span><button[^>]*>Place anyway<\/button>/.test(rowOf(h, "HR-EMP-00382")));
  ok("071 full: the button is described by the name and the words",
     /aria-describedby="pos-un-n-\d+ pos-un-f-\d+">Place anyway/.test(rowOf(h, "HR-EMP-00382")));
  ok("071 E1: a seat with 0 places has room", rowOf(h, "HR-EMP-00384").includes(">Place in seat</button>"));
  ok("071 no matching seat: no button", !rowOf(h, "HR-EMP-00383").includes("<button"));
  ok("071 Q3: of two matching seats the one with room is used",
     h.includes("1 Packer · matching seat:") && h.includes(">B Packer · Sector 34</button>")
     && rowOf(h, "HR-EMP-00385").includes("P-PackB") && rowOf(h, "HR-EMP-00385").includes("Place in seat"));

  const btn = { focus() { t.focused.push("row-button"); } };
  t.ctx.posUnPlace("HR-EMP-00382", "P-Counter", btn);
  const x = t.ctx.__els["pos-full-x"].innerHTML;
  ok("071 confirm opens, focus on Cancel",
     t.ctx.__els["pos-full"].classList.contains("open") && t.focused[t.focused.length - 1] === "pos-full-no");
  ok("071 confirm names the seat, its places and people",
     x.includes("<strong>Counter Staff · Sector 34</strong> has 1 places and 1 people in them."));
  ok("071 confirm says the seat gets one more place", x.includes("Ravi Kumar in it, the seat gets one more place: 2 in all.")
     && x.includes("really needs another Counter."));
  t.ctx.posFullClose();
  ok("071 Cancel closes, focus back on the row button, nothing sent, nothing changed",
     !t.ctx.__els["pos-full"].classList.contains("open") && t.focused[t.focused.length - 1] === "row-button"
     && t.calls.length === 0 && t.ctx.posById("P-Counter").seats === 1);
}

/* 071 step 5 onwards: the dialog opened from the tray. Async, so chained below. */
function withCands(t) {
  const kids = {};
  Object.defineProperty(t.ctx.__els["pos-p-list"], "children", { get() {
    return (this.innerHTML.match(/id="pos-cand-[^"]+"/g) || []).map((m) => (kids[m] = kids[m]
      || { id: m.slice(4, -1), style: {}, setAttribute(k, v) { this[k] = v; } }));
  } });
  t.cands = [{ employee: "HR-EMP-00380", name: "Ravi Kumar", designation: "Cashier", branch: "Sector 34", free: 100 },
             { employee: "HR-EMP-00382", name: "Ravi Kumar", designation: "Counter", branch: "Sector 34", free: 100 },
             { employee: "HR-EMP-00381", name: "Anjali Saini", designation: "Cashier", branch: "Sector 34", free: 100 },
             { employee: "HR-EMP-00999", name: "Zed Other", designation: "", branch: "", free: 100 }];
  // Like candidates_for: a typed name narrows by name.
  t.fetch = (m, a) => Promise.resolve(m.endsWith("candidates_for")
    ? { rows: t.cands.filter((c) => !a.q || c.name.toLowerCase().includes(a.q.toLowerCase())) }
    : { rows: [], held: 0, free: 100 });
  t.kid = (emp) => kids['id="pos-cand-' + emp + '"'];
  return t;
}
const tick = () => new Promise((r) => setImmediate(r));
async function unChecks() {
  {
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.ctx.posUnPlace("HR-EMP-00381", "P-Cashier", { focus() {} });
    await tick();
    ok("071 dialog from the tray: open, name in the search, picked by ID",
       E["pos-person"].classList.contains("open") && E["pos-p-q"].value === "Anjali Saini" && t.ctx.POS.picked === "HR-EMP-00381");
    ok("071 dialog: the context line names the seat, no raise sentence",
       E["pos-p-ctx"].textContent === "For Cashier · Sector 34 (2 of 3)." && E["pos-p-ctx"].style.display === "");
    ok("071 dialog: focus on Put them in", t.focused[t.focused.length - 1] === "pos-p-save");
    ok("071 dialog: share 100, Permanently, approvals off",
       E["pos-p-weight"].value === 100 && E["pos-p-type"].value === "Permanent" && E["pos-p-delegate"].checked === false);
  }
  {
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.ctx.posUnPlace("HR-EMP-00380", "P-Cashier", { focus() {} });
    await tick();
    const l = E["pos-p-list"].innerHTML;
    ok("071 duplicate names: each candidate line carries the ID",
       l.includes("HR-EMP-00380 - Cashier - Sector 34 - free") && l.includes("HR-EMP-00382 - Counter - Sector 34 - free"));
    ok("071 duplicate names: the ID-picked one is the one marked",
       t.ctx.POS.picked === "HR-EMP-00380" && t.kid("HR-EMP-00380")["aria-pressed"] === "true"
       && t.kid("HR-EMP-00382")["aria-pressed"] === "false");
    E["pos-p-q"].value = "Zed";
    await t.ctx.posPickSearch();
    ok("071 a new search without them clears the pick", t.ctx.POS.picked === null);
    await t.ctx.posPickSave();
    ok("071 and Save asks to choose, sending nothing",
       E["pos-person-err"].textContent === "Choose somebody from the list first."
       && !t.calls.some((c) => c[0].endsWith("assign_person")));
  }
  {
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.ctx.posUnPlace("HR-EMP-00382", "P-Counter", { focus() {} });
    t.ctx.posFullGo();
    await tick();
    ok("071 after Add a place: the dialog says the count goes up",
       !E["pos-full"].classList.contains("open") && E["pos-person"].classList.contains("open")
       && E["pos-p-ctx"].textContent === "For Counter Staff · Sector 34 (1 of 1). When you press Put them in, the seat goes from 1 to 2 places.");
  }
  {
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.ctx.posPickPerson();
    ok("071 editor path unchanged: no editor seat, no dialog", !E["pos-person"].classList.contains("open"));
    t.box("pos-e-name", { value: "P-Cashier" });
    t.ctx.posPickPerson();
    await tick();
    ok("071 editor path: empty search, no context line, nobody picked",
       E["pos-person"].classList.contains("open") && E["pos-p-q"].value === "" && E["pos-p-ctx"].style.display === "none"
       && t.ctx.POS.picked === null && t.calls[0][1].position === "P-Cashier");
  }
  {
    // Review m2: half a place free starts the share at 50, so it fills first time.
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.ctx.POS.rows = UNROWS2.map((r) => (r.id === "P-Cashier" ? Object.assign({}, r, { filled: 2.5, open: 0.5 }) : r));
    t.ctx.posUnPlace("HR-EMP-00381", "P-Cashier", { focus() {} });
    await tick();
    ok("071 m2: half a place free starts the share at 50", E["pos-p-weight"].value === 50);
  }
  /* step 6: saving */
  const after = (gone, seatId) => ({
    rows: UNROWS2.map((r) => (r.id === seatId ? Object.assign({}, r, { filled: r.filled + 1, seats: Math.max(r.seats, r.filled + 1),
                                                                     open: 0 }) : r)),
    may_edit: true, unseated: UN2.filter((p) => p.employee !== gone), active_people: 40, as_at: "2026-10-22",
  });
  async function saving(emp, seatId, answer, check) {
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.box("pos-un-flash");
    let release;
    const gate = new Promise((r) => { release = r; });
    const base = t.fetch;
    t.fetch = (m, a) => (m.endsWith("assign_person") ? gate.then(() => answer.assign())
      : m.endsWith("position_table") ? Promise.resolve(answer.table()) : base(m, a));
    t.ctx.posUnPlace(emp, seatId, { focus() {} });
    if (t.ctx.POS.pickFrom.raise) t.ctx.posFullGo();
    await tick();
    const saved = t.ctx.posPickSave();
    await tick();
    const mid = { text: E["pos-p-save"].textContent, disabled: E["pos-p-save"].disabled, open: E["pos-person"].classList.contains("open") };
    release();
    await saved; await tick();
    check(t, E, mid, t.calls.filter((c) => c[0].endsWith("assign_person")).map((c) => c[1]));
  }
  await saving("HR-EMP-00381", "P-Cashier",
    { assign: () => ({ name: "A-1" }), table: () => after("HR-EMP-00381", "P-Cashier") },
    (t, E, mid, sent) => {
      ok("071 save: Putting them in…, disabled, dialog still open", mid.text === "Putting them in…" && mid.disabled && mid.open);
      ok("071 save: a seat with room sends add_place 0, by employee ID",
         sent.length === 1 && sent[0].add_place === 0 && sent[0].employee === "HR-EMP-00381" && sent[0].position === "P-Cashier");
      const h = t.layer();
      ok("071 success: dialog closed, the note, focus on it",
         !E["pos-person"].classList.contains("open") && E["pos-p-save"].textContent === "Put them in" && !E["pos-p-save"].disabled
         && h.includes('<div class="pos-note ok" role="status" id="pos-un-flash" tabindex="-1">Anjali Saini is now in Cashier · Sector 34.</div>')
         && t.focused[t.focused.length - 1] === "pos-un-flash");
      ok("071 success: title, first line, branch, role and seat counts drop by one",
         h.includes("In no seat · 5 people") && h.includes("5 of 40 active people") && h.includes("Sector 34 · 3")
         && h.includes("1 Cashier · matching seat:") && h.includes("(3 of 3)") && !h.includes(">HR-EMP-00381<"));
      ok("071 success: the tile drops by one", E["pos-tiles"].innerHTML.includes('onclick="posUnseatedSheet()"><div class="n">5</div><div class="l">IN NO SEAT'));
      t.ctx.posUnseatedSheet();
      ok("071 the note shows once", !t.layer().includes("is now in"));
    });
  await saving("HR-EMP-00382", "P-Counter",
    { assign: () => ({ name: "A-2" }), table: () => after("HR-EMP-00382", "P-Counter") },
    (t, E, mid, sent) => {
      ok("071 Place anyway sends add_place 1", sent.length === 1 && sent[0].add_place === 1 && sent[0].employee === "HR-EMP-00382");
      ok("071 after Add a place the seat reads one up", t.layer().includes("Ravi Kumar is now in Counter Staff · Sector 34."));
    });
  await saving("HR-EMP-00381", "P-Cashier",
    { assign: () => { throw Object.assign(new Error("Could not reach the server."), { kind: "network" }); }, table: () => after("", "") },
    (t, E) => {
      ok("071 no answer, still unseated: the connection message, dialog open, button back",
         E["pos-person-err"].textContent === "Could not reach the server, so Anjali Saini is not in the seat. Check your connection and press Put them in again."
         && E["pos-person"].classList.contains("open") && E["pos-p-save"].textContent === "Put them in" && !E["pos-p-save"].disabled);
    });
  await saving("HR-EMP-00382", "P-Counter",
    { assign: () => { throw Object.assign(new Error("Could not reach the server."), { kind: "network" }); }, table: () => after("", "") },
    (t, E) => {
      ok("071 no answer after Add a place: says the seat still has its places",
         E["pos-person-err"].textContent === "Could not reach the server, so Ravi Kumar is not in the seat and the seat still has 1 places. Check your connection and press Put them in again.");
    });
  await saving("HR-EMP-00381", "P-Cashier",
    { assign: () => { throw Object.assign(new Error("Cashier has 3 seat(s) and would be filled 1.33 times over."), { kind: "refused", server: true }); }, table: () => after("", "") },
    (t, E) => {
      ok("071 a refusal is shown as it comes, and the list is not re-asked",
         E["pos-person-err"].textContent === "Cashier has 3 seat(s) and would be filled 1.33 times over."
         && !t.calls.some((c) => c[0].endsWith("position_table")));
    });
  await saving("HR-EMP-00381", "P-Cashier",
    { assign: () => { throw Object.assign(new Error("Could not reach the server."), { kind: "network" }); }, table: () => after("HR-EMP-00381", "P-Cashier") },
    (t, E) => {
      ok("071 answer lost but saved: the success note, not the error",
         E["pos-person-err"].textContent === "" && t.layer().includes("Anjali Saini is now in Cashier · Sector 34."));
    });
  {
    // US-7: the last person placed.
    const t = withCands(unContext(true)), E = t.ctx.__els;
    t.box("pos-un-flash");
    t.ctx.POS.unseated = [UN2[1]];
    t.fetch = (m) => Promise.resolve(m.endsWith("position_table") ? Object.assign(after("", ""), { unseated: [] })
      : m.endsWith("candidates_for") ? { rows: [t.cands[2]] } : { name: "A-3", rows: [], held: 0, free: 100 });
    t.ctx.posUnPlace("HR-EMP-00381", "P-Cashier", { focus() {} });
    await tick();
    await t.ctx.posPickSave(); await tick();
    ok("071 the last one placed: 0 people and the empty sentence",
       t.layer().includes("In no seat · 0 people") && t.layer().includes("Everybody active is in a seat now"));
  }
  /* step 7: Escape closes only the top layer */
  function escContext() {
    const t = withCands(unContext(true)), keys = [];
    t.ctx.document.addEventListener = (type, fn) => { if (type === "keydown") keys.push(fn); };
    t.ctx.posWire();
    t.esc = (extra) => keys.forEach((fn) => fn(Object.assign({ key: "Escape", defaultPrevented: false }, extra || {})));
    t.ctx.posUnseatedSheet();
    t.row = { focus() { t.focused.push("row-button"); } };
    return t;
  }
  {
    const t = escContext(), E = t.ctx.__els;
    t.ctx.posUnPlace("HR-EMP-00381", "P-Cashier", t.row);
    await tick();
    t.esc();
    ok("071 Escape with the dialog open: the dialog closes, the tray stays, focus back on the row",
       !E["pos-person"].classList.contains("open") && t.ctx.POS.sheet && t.layer() !== ""
       && t.focused[t.focused.length - 1] === "row-button");
    t.esc();
    ok("071 a second Escape closes the tray", t.ctx.POS.sheet === null && t.layer() === "");
  }
  {
    const t = escContext(), E = t.ctx.__els;
    t.ctx.posUnPlace("HR-EMP-00382", "P-Counter", t.row);
    t.esc();
    ok("071 Escape with the confirm open: only the confirm closes, no dialog, focus on the row",
       !E["pos-full"].classList.contains("open") && !E["pos-person"].classList.contains("open") && t.ctx.POS.sheet
       && t.focused[t.focused.length - 1] === "row-button" && t.calls.length === 0);
  }
  {
    const t = escContext();
    t.esc({ defaultPrevented: true });
    ok("071 an Escape another dialog handled leaves the tray", t.ctx.POS.sheet && t.layer() !== "");
    t.ctx.document.querySelector = (q) => (q === ".gp-backdrop.open" ? {} : null);
    t.esc();
    ok("071 any other dialog open leaves the tray", t.ctx.POS.sheet && t.layer() !== "");
    t.ctx.document.querySelector = () => null;
    t.esc({ key: "Enter" });
    ok("071 other keys do nothing", t.ctx.POS.sheet && t.layer() !== "");
    t.esc();
    ok("071 nothing on top: Escape closes the tray", t.ctx.POS.sheet === null);
  }
}

/* ── 23. slice 072: seats follow the reporting line ──────────────────────
 *
 * In Reporting lines each person is drawn under the seat of their Reports To
 * manager (`manager` on the person). These run the REAL page in jsdom, so the
 * drawn markup is what a browser gets. The oracle below works out where each
 * person belongs from the rows and the manager keys alone - it never asks the
 * page's own placement code (SEC-4 a). */
const S70 = (() => {
  const P = (employee, manager, extra) => Object.assign({ employee, assignment: "A-" + employee, name: "N " + employee,
    weight: 100, type: "Permanent", covering: false, hired_on: null, leaving: null }, manager === undefined ? {} : { manager }, extra || {});
  const R = (id, title, parent, people, extra) => Object.assign({ id, title, reports_to: parent || "", reports_to_title: "",
    branch: "Head Office", department: "Accounts", designation: title, grade: "", company: "DTC", status: "Active",
    key: false, seats: people.length || 1, filled: people.length, open: people.length ? 0 : 1, opening: null,
    leaving_on: null, people }, extra || {});
  return () => [
    R("OWN", "Owner", "", [P("E-OWN", "")]),
    R("CFO", "Chief Financial Officer", "OWN", [P("E-CFO", "E-OWN")]),
    R("RH", "Retail Head", "OWN", [P("E-RH", "E-OWN")]),
    R("OE", "Office Executive", "OWN", [P("OE1", "E-OWN"), P("OE2", "E-OWN"), P("OE3", "E-CFO"), P("OE4", "E-CFO"),
                                        P("OE5", "E-CFO"), P("OE6", "E-CFO")]),
    R("BO", "Back Office", "OWN", [P("B1", "E-OWN"), P("B2", "E-CFO"), P("B3", "E-BX")], { seats: 4, open: 1 }),
    R("BX", "Backoffice Executive", "BO", [P("E-BX", "B1")]),
    R("MIS", "MIS", "OWN", [P("M1", "E-CFO")], { seats: 2, open: 1 }),
    R("AUD", "Store Auditor", "OWN", [P("A1", "E-RH")]),
    R("PK", "Packing", "RH", [P("K1", "E-NOSEAT"), P("K2"), P("K3", "E-GCFO")]),
    R("FS", "Floor Supervisor", "RH", [P("F1", "E-RH"), P("F2", "F1")]),
    R("AMN", "Area Manager North", "RH", [P("E-AM", "E-RH", { weight: 50 })]),
    R("AME", "Area Manager East", "RH", [P("E-AM", "E-RH", { weight: 50, assignment: "A-E-AM-2" })]),
    R("ST", "Store Staff", "RH", [P("S1", "E-AM")]),
    R("XP", "X Permanent", "RH", [P("E-X", "E-RH", { weight: 60 })]),
    R("XC", "X Covering", "RH", [P("E-X", "E-RH", { type: "Covering", covering: true, assignment: "A-E-X-2" })]),
    R("XS", "X Staff", "RH", [P("X1", "E-X")]),
    R("SEC", "Secretary Desk", "CFO", [P("E-OWN", "", { assignment: "A-E-OWN-2" })]),
    R("CA1", "Cashier", "RH", [P("C1", "E-CFO"), P("C1b", "E-RH")]),
    R("CA2", "Cashier", "RH", [P("C2", "E-RH")]),
    R("GRP", "Group CFO", "", [P("E-GCFO", "")], { company: "Other Co" }),
    R("HID", "Area Manager", "SEAT-HIDDEN-SNTL", [P("H1", "MGR-ABSENT-SNTL"), P("H2", "E-CFO")]),
  ];
})();

/* The oracle (spec §7), from rows and manager keys only. Returns, per
   assignment, the seat whose box the person should be drawn in and the box
   kind: { seat, copyUnder } - copyUnder null means the seat's own box. */
function oracle072(rows, filtered) {
  const byEmp = {};
  rows.forEach((r) => r.people.forEach((p) => { (byEmp[p.employee] = byEmp[p.employee] || []).push({ r, p }); }));
  const want = {};
  rows.forEach((r) => r.people.forEach((p) => {
    let under = null;
    const held = (p.manager ? byEmp[p.manager] || [] : []).filter((x) => x.r.company === r.company);
    if (held.length && !held.some((x) => x.r.id === r.id || x.r.id === r.reports_to) && (!filtered || filtered(r))) {
      const perm = held.filter((x) => x.p.type === "Permanent");
      const pool = perm.length ? perm : held;
      const top = Math.max(...pool.map((x) => x.p.weight));
      under = pool.filter((x) => x.p.weight === top).map((x) => x.r).sort((a, b) => (a.title + a.id < b.title + b.id ? -1 : 1))[0].id;
    }
    want[p.assignment] = { seat: r.id, copyUnder: under };
  }));
  return want;
}

async function seats072() {
  let JSDOM, VirtualConsole;
  try { ({ JSDOM, VirtualConsole } = require("jsdom")); }
  catch (e) { problems.push("slice 072 checks need jsdom (npm ci): " + e.message); return; }
  const { readPortalSource } = require("./lib/portal_source");
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { if (!/Unexpected token '\{'/.test(String(e && e.message))) console.error(e); });
  const dom = new JSDOM(readPortalSource(), {
    virtualConsole: vc, runScripts: "dangerously", pretendToBeVisual: true, url: "http://grace.localhost/hrms-employee",
    beforeParse(w) {
      w.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: {} }), text: () => Promise.resolve("") });
      w.frappe = { call: () => Promise.resolve({ message: {} }), csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: { escape_html: (s) => s } };
    },
  });
  const { window } = dom, doc = window.document;
  window.Element.prototype.scrollIntoView = function () {};
  await new Promise((r) => setTimeout(r, 300));
  const W = window;
  const body = () => doc.getElementById("pos-body");
  const idOf = (b) => { const m = (b.getAttribute("onclick") || "").match(/\('([^']+)'\)/); return m ? m[1] : null; };

  /* Draw `rows` with every fold open, in the given arrangement. */
  function draw(rows, arrange, opts) {
    opts = opts || {};
    const P = W.POS;
    P.rows = rows; P.may_edit = true; P.unseated = opts.unseated === undefined ? [{ employee: "E-NOSEAT", name: "Neeraj Sood", no_manager: false }] : opts.unseated;
    P.collapsed = {}; P.expanded = {}; P.ungrouped = {}; P._saved = null; P._findId = null; P._focusNext = false;
    rows.forEach((r) => { P.expanded[r.id] = true; });
    doc.getElementById("pos-f-view").value = "tree";
    doc.getElementById("pos-f-arrange").value = arrange || "reporting";
    ["pos-f-branch", "pos-f-dept", "pos-f-role", "pos-f-open"].forEach((id) => {
      const el = doc.getElementById(id), v = (opts.filter || {})[id] || "";
      if (v && ![...el.options].some((o) => o.value === v)) el.insertAdjacentHTML("beforeend", '<option value="' + v + '">' + v + "</option>");
      el.value = v;
    });
    W.POS_NAMES_SHOWN = opts.names || 1000;
    W.posPaint();
    W.POS_NAMES_SHOWN = 3;
    return body().innerHTML;
  }
  /* Every drawn seat box: its id, its names, the box it hangs under. */
  function boxes() {
    return [...body().querySelectorAll(".oc-tree .oc-box")].map((b) => {
      const node = b.closest(".oc-node");
      let br = node.parentElement.closest(".oc-branch");
      if (br && br.querySelector(":scope > .oc-node") === node) br = br.parentElement.closest(".oc-branch");
      while (br && br.classList.contains("oc-hang-slot")) br = br.parentElement.closest(".oc-branch");
      const pbox = br && br.querySelector(":scope > .oc-node > .oc-box");
      return { el: b, id: idOf(b), copy: b.classList.contains("copy"), parent: pbox ? idOf(pbox) : null,
               title: b.querySelector(".ti").textContent,
               names: [...b.querySelectorAll(".oc-who:not(.oc-empty) > span:last-child")].map((s) => s.firstChild.textContent)
                 .filter((t) => !/^\+\d+ more/.test(t)),
               node };
    });
  }
  const seatOfCopy = (id) => (W.POS.place.byId[id] || {}).seat;

  /* 22a. every person is where the oracle says, exactly once (SEC-4 a, N1, AC-19) */
  {
    const rows = S70();
    draw(rows);
    const drawn = boxes(), want = oracle072(rows), seen = {};
    drawn.forEach((b) => b.names.forEach((nm) => {
      const r = rows.find((x) => x.id === (b.copy ? seatOfCopy(b.id).id : b.id));
      const p = r && r.people.find((q) => q.name === nm);
      if (!p) { ok("072: a drawn name belongs to the box's seat", false, nm + " in " + b.id); return; }
      seen[p.assignment] = (seen[p.assignment] || 0) + 1;
      const w = want[p.assignment];
      ok("072: " + nm + " is in the box the oracle says",
         w.copyUnder ? (b.copy && b.parent === w.copyUnder) : (!b.copy && b.id === w.seat), JSON.stringify([b.id, b.parent, w]));
    }));
    const all = rows.reduce((a, r) => a + r.people.length, 0);
    ok("072 N1: every assignment drawn exactly once", Object.keys(seen).length === all && Object.values(seen).every((n) => n === 1),
       Object.keys(seen).length + " of " + all);
    // The oracle must be able to fail: swap two managers and it disagrees.
    const swapped = S70();
    swapped.find((r) => r.id === "OE").people[0].manager = "E-CFO";
    const w2 = oracle072(swapped);
    ok("072: the oracle notices a swapped manager", w2["A-OE1"].copyUnder === "CFO" && want["A-OE1"].copyUnder === null);

    const by = (id) => drawn.filter((b) => b.id === id);
    const one = (id) => by(id)[0] || { names: [], el: doc.createElement("i"), parent: null };
    const copies = drawn.filter((b) => b.copy);
    ok("072 AC-12: Office Executive home has 2, a copy under the CFO has the 4",
       one("OE").names.length === 2 && copies.some((c) => seatOfCopy(c.id).id === "OE" && c.parent === "CFO" && c.names.length === 4));
    ok("072 AC-13 (Q5): a head and team in one seat stay home", one("FS").names.length === 2 && !copies.some((c) => seatOfCopy(c.id).id === "FS"));
    ok("072 AC-14: a manager in no seat, or not sent, keeps them home", one("PK").names.length === 3);
    ok("072 Q6: a manager in another company keeps them home", one("PK").names.includes("N K3"));
    ok("072 AC-15 (G3): a manager in two seats, one the parent, keeps them home", one("OE").names.includes("N OE1"));
    ok("072 AC-16: Permanent beats covering, then title A-Z",
       copies.some((c) => seatOfCopy(c.id).id === "XS" && c.parent === "XP")
       && copies.some((c) => seatOfCopy(c.id).id === "ST" && c.parent === "AME"));
    ok("072 AC-23: a home with nothing left is not drawn", !by("AUD").length && copies.some((c) => seatOfCopy(c.id).id === "AUD" && c.parent === "RH"));
    ok("072 AC-24: a home with an open slot stays, saying where its people are",
       by("MIS").length === 1 && /None here: all 1 shown under Chief Financial Officer/.test(one("MIS").el.textContent)
       && /open/.test(one("MIS").el.querySelector(".oc-box-hd").textContent));
    ok("072 AC-22: the open tag is on the home only", copies.every((c) => !c.el.querySelector(".oc-tag.v"))
       && one("BO").el.querySelector(".oc-tag.v"));
    ok("072 AC-26: the seat under Back Office hangs under its home", one("BX").parent === "BO");
    ok("072 the 64 case: a copy of Back Office hangs under the seat below it",
       copies.some((c) => seatOfCopy(c.id).id === "BO" && c.parent === "BX"));
    ok("072 AC-18 (C1): no copy has a fold button or anything under it",
       copies.every((c) => !c.node.querySelector(".oc-toggle") && !c.node.parentElement.querySelector(":scope > .oc-kids, :scope > .oc-fam")));
    const cfoKids = drawn.filter((b) => b.parent === "CFO").map((b) => b.copy);
    ok("072 AC-18 (C3): under the CFO the real seats come before the copies",
       cfoKids.length > 2 && cfoKids.indexOf(true) > cfoKids.lastIndexOf(false), JSON.stringify(cfoKids));
    ok("072 AC-20 (C4): a seat with a copy is never grouped", !body().innerHTML.includes("grp:") && by("CA1").length === 1 && by("CA2").length === 1);
    const pd = W.POS.place.byId[copies.find((c) => seatOfCopy(c.id).id === "OE").id].people[0];
    ok("072 PRIV-1/G: a copy holds the same person objects, so a plan key travels with the person",
       rows.find((r) => r.id === "OE").people.indexOf(pd) >= 0);
  }

  /* 22b. a Reports To loop draws and stops (AC-21) */
  {
    const P = (e, m) => ({ employee: e, assignment: "A-" + e, name: "N " + e, weight: 100, type: "Permanent", manager: m });
    const rows = [Object.assign({}, S70()[0]), { id: "X", title: "Seat X", reports_to: "OWN", branch: "", department: "", company: "DTC",
      status: "Active", seats: 1, filled: 1, open: 0, people: [P("PX", "PY")] },
      { id: "Y", title: "Seat Y", reports_to: "OWN", branch: "", department: "", company: "DTC", status: "Active", seats: 1, filled: 1, open: 0,
        people: [P("PY", "PX")] }];
    draw(rows);
    const c = boxes().filter((b) => b.copy);
    ok("072 AC-21: a loop gives a copy each way and drawing ends",
       c.length === 2 && c.some((b) => b.parent === "Y") && c.some((b) => b.parent === "X"));
  }

  /* 22c. the words on the boxes (AC-27 - AC-31, Q6 words) */
  {
    draw(S70(), "reporting", { names: 3 });
    const drawn = boxes(), copies = drawn.filter((b) => b.copy);
    const copyOf = (seat) => copies.find((c) => seatOfCopy(c.id).id === seat);
    const txt = (b) => (b ? b.el.textContent.replace(/\s+/g, " ") : "");
    ok("072 AC-27: a copy reads branch and its people, then the same-seat line",
       /Head Office · 4 people/.test(txt(copyOf("OE"))) && /\+1 more here/.test(txt(copyOf("OE")))
       && /Same seat as under Owner · 6 in all/.test(txt(copyOf("OE"))), txt(copyOf("OE")));
    ok("072 AC-28: a copy whose home is not drawn reads Set up under", /Set up under Owner$/.test(txt(copyOf("AUD")).trim()), txt(copyOf("AUD")));
    ok("072 AC-29: a home says how many are shown elsewhere",
       /4 more shown under Chief Financial Officer/.test(txt(drawn.find((b) => b.id === "OE")))
       && /2 more shown under 2 other managers/.test(txt(drawn.find((b) => b.id === "BO"))));
    ok("072 AC-31: a parent outside the view is never named",
       /Same seat as under a seat above your view · 2 in all/.test(txt(copyOf("HID"))));
    const html = body().innerHTML;
    ok("072 SEC-3: no hidden seat id or unknown manager id is echoed", !html.includes("SEAT-HIDDEN-SNTL") && !html.includes("MGR-ABSENT-SNTL"));
    ok("072 AC-32: a copy is dashed and its line is inside the button",
       copies.every((c) => c.el.tagName === "BUTTON" && c.el.querySelector(".oc-same")) && copies.every((c) => c.el.querySelector(".oc-same svg[aria-hidden=true]")));
  }

  /* 22d. nothing else moves (AC-34, AC-52, AC-53, AC-54) */
  {
    const bare = () => S70().map((r) => Object.assign({}, r, { people: r.people.map((p) => { const q = Object.assign({}, p); delete q.manager; return q; }) }));
    for (const arr of ["branch", "department"]) {
      ok("072 AC-52: " + arr + " view is byte-identical with and without manager keys", draw(S70(), arr) === draw(bare(), arr));
    }
    draw(S70()); const t1 = doc.getElementById("pos-tiles").innerHTML;
    draw(bare()); const t2 = doc.getElementById("pos-tiles").innerHTML;
    ok("072 AC-34: the tiles do not change with manager keys", t1 === t2);
    const plain = draw(bare());
    ok("072 AC-54: no manager keys, no copies and no grey lines", !/class="oc-box[^"]* copy/.test(plain) && !plain.includes("oc-same"));
    const card = W.ocNodeCard({ id: "x", title: "T", subtitle: "S", open: 1, people: [{ name: "Ann Bee" }], flags: [] }, false);
    ok("072 AC-53: the Organisation card is unchanged without the new fields",
       card === '<div class="oc-node"><button type="button" class="oc-box" style="text-align:left;font:inherit;width:100%;cursor:pointer"'
         + ' onclick="ocFocus(\'x\')"><div class="oc-box-hd"><span class="ti">T</span><span class="oc-tag v">open</span></div>'
         + '<div class="sub">S</div><div class="oc-who"><span class="av">AB</span><span>Ann Bee</span></div></button></div>', card);
    // PRIV-1 (b): private keys on a person in a copy change no box.
    const shape = () => boxes().map((b) => [b.id, b.copy, b.parent, b.names.join("|"), (b.el.querySelector(".oc-same") || {}).textContent || ""].join("~")).join("\n");
    draw(S70()); const s1 = shape();
    const priv = S70();
    priv.forEach((r) => { r.opening = "OPN-SNTL"; r.people.forEach((p) => { p.plan = { note: "PLAN-SNTL" }; p.hired_on = "2026-10-01"; }); });
    draw(priv); const s2 = shape();
    ok("072 PRIV-1 b: plans, openings and hire dates do not move, add or remove a box", s1 === s2);
  }

  /* 22e. the view's name and its note (AC-33, Q4) */
  {
    const note = () => (body().querySelector(".pos-view-note") || {}).textContent || "";
    ok("072 AC-33: the Arrange by option reads Reporting lines",
       doc.querySelector('#pos-f-arrange option[value="reporting"]').textContent === "Reporting lines");
    draw(S70());
    ok("072 AC-33: the Reporting lines note, word for word", note() === "Each person is shown under the seat of their manager, as set in "
       + "Reports To on their employee record. A seat shared by people with different managers shows once under each manager. "
       + "Open slots and the seats under it stay on the seat's own box.", note());
    for (const arr of ["branch", "department"]) {
      draw(S70(), arr);
      ok("072 AC-33: the " + arr + " note, word for word",
         note() === "One box per seat, with everyone in it. To see people under their managers, choose Arrange by: Reporting lines.", note());
    }
    ok("072 AC-33: the print heading says Reporting lines", W.posPrintHead("reporting").includes("Reporting lines"));
    ok("072 Q4: the old name is gone from the page", !doc.documentElement.innerHTML.includes("Who reports to whom"));
  }

  /* 22f. the seat tray (AC-35 - AC-42, AC-50, SEC-3) */
  {
    const layer = () => doc.getElementById("pos-layer");
    const tray = (id) => { W.posCloseSheet(true); W.posSeatSheet(id); return layer().textContent.replace(/\s+/g, " "); };
    draw(S70());
    const copyId = (seat, under) => Object.keys(W.POS.place.byId).find((k) => W.POS.place.byId[k].seat.id === seat && W.POS.place.byId[k].under === under);
    let t = tray("BO");
    ok("072 AC-35: Where it shows lists the home and each copy",
       t.includes("Where it shows on this chart") && t.includes("Under Owner: its own box, 1 person, 1 open, 1 seat under it")
       && t.includes("Under Chief Financial Officer: 1 person") && t.includes("Under Backoffice Executive: 1 person"), t);
    ok("072 AC-35: the box opened is marked", /its own box, 1 person, 1 open, 1 seat under itYou opened this one/.test(t));
    ok("072 AC-37: the note says how people are placed",
       t.includes("People are placed by Reports To on their employee record. To move someone, change their Reports To; "
                  + "the chart follows the next time it opens. The seat itself stays under Owner."));
    ok("072 AC-66: each Show button says what it shows",
       [...layer().querySelectorAll(".pos-places button")].every((b) => /^Show it on the chart: Under /.test(b.getAttribute("aria-label"))));
    ok("072 AC-39: lines name the manager and their seat",
       t.includes("Reports to N E-OWN (Owner)") && t.includes("Reports to N E-CFO (Chief Financial Officer)") && t.includes("Reports to N E-BX (Backoffice Executive)"));
    t = tray(copyId("BO", "CFO"));
    ok("072 AC-42: a copy opens the same seat's tray", t.includes("Back Office") && t.includes("3 of 4") && /Under Chief Financial Officer: 1 personYou opened this one/.test(t));
    ok("072 AC-42: Change edits the seat, not the copy", layer().innerHTML.includes("posSheetChange('BO')"));
    ok("072 review M1: the tray says the seat is set up under its parent, as the prototype does",
       t.includes("Head Office · Accounts · set up under Owner") && !t.includes("reports to Owner"), t.slice(0, 120));
    t = tray(copyId("AUD", "RH"));
    ok("072 AC-36: a home not drawn says why", t.includes("Its own box under Owner is not drawn: nobody there reports along that line, no slot is open and no seat hangs under it.") && !t.includes("its own box,"));
    ok("072 AC-39: same seat", tray("FS").includes("Reports to N F1, also in this seat"));
    t = tray("PK");
    ok("072 AC-39/AC-50: an unseated manager is named for HR", t.includes("Reports to Neeraj Sood, who is in no seat"));
    ok("072 AC-39: a manager the reply does not carry is not named", t.includes("Reports to a manager who is not on this chart"));
    ok("072 AC-39: no manager on record", tray("OWN").includes("No manager on their record"));
    ok("072 SEC-3: the tray never echoes an unknown manager or hidden seat", !layer().innerHTML.includes("MGR-ABSENT-SNTL")
       && !tray("HID").includes("MGR-ABSENT-SNTL") && !layer().innerHTML.includes("SEAT-HIDDEN-SNTL"));
    ok("072 AC-41: a seat drawn once has no Where it shows", !tray("CFO").includes("Where it shows"));
    // Show: closes the tray, opens the way, focuses the copy (AC-38).
    W.POS.collapsed = { CFO: true }; W.posPaint();
    tray("BO");
    const show = [...layer().querySelectorAll(".pos-places button")][1];
    show.click();
    ok("072 AC-38: Show closes the tray", layer().innerHTML === "");
    const focused = doc.activeElement;
    ok("072 AC-38: Show opens the fold and focuses the copy", focused && focused.classList.contains("copy")
       && focused.classList.contains("pos-first") && /Back Office/.test(focused.textContent) && !W.POS.collapsed.CFO);
    // A reader without HR scope: never the unseated manager's name (AC-50).
    draw(S70(), "reporting", { unseated: null });
    t = tray("PK");
    ok("072 AC-50: without HR scope the unseated manager is not named", !layer().innerHTML.includes("Neeraj") && t.includes("Reports to a manager who is not on this chart"));
    // AC-40, Q2/P-25: the split advice is gone; the records notes only outside Reporting lines.
    const src = fs.readFileSync(PORTAL, "utf8");
    ok("072 AC-40: the split advice is gone from every view", !src.includes("needs splitting first") && !src.includes("Give the head a seat of their own"));
    W.POS.records = { mismatches: [], mixed: [{ position: "BO", manager: "E-OWN", manager_name: "Own", count: 1 }, { position: "BO", manager: "E-CFO", manager_name: "Cfo", count: 1 }] };
    draw(S70());
    ok("072 AC-40: in Reporting lines the records notes give way", !tray("BO").includes("This seat holds the people of"));
    draw(S70(), "branch");
    t = tray("BO");
    ok("072 AC-40/41: in Branch they show as before, without the new section or lines",
       t.includes("This seat holds the people of 2 managers") && !t.includes("Where it shows") && !t.includes("Reports to N"));
    W.POS.records = null;
    W.posCloseSheet(true);
  }

  /* 22g. Find, filters and the outline (AC-43 - AC-48, G1, G2) */
  {
    const pick = (q) => {
      W.posFind(q);
      const b = doc.querySelector("#pos-find-res .pos-hit");
      if (b) b.click();
      return doc.activeElement;
    };
    draw(S70()); W.POS.expanded = {}; W.POS.collapsed = {}; W.posPaint();
    let f = pick("N OE3");
    ok("072 AC-44: a person in a copy is found in the copy", f && f.classList.contains("copy") && f.classList.contains("pos-first")
       && /Office Executive/.test(f.textContent) && W.POS.expanded.CFO);
    draw(S70()); W.POS.expanded = {}; W.posPaint();
    f = pick("N OE1");
    ok("072 AC-45: a person at home is found at home", f && !f.classList.contains("copy") && /Office Executive/.test(f.textContent));
    draw(S70()); W.POS.expanded = {}; W.posPaint();
    f = pick("Store Auditor");
    ok("072 AC-45/G2: a seat whose own box is not drawn is found at its copy", f && f.classList.contains("copy") && /Store Auditor/.test(f.textContent));

    // G1: a branch filter that keeps a manager seat and a shared seat.
    const noida = () => S70().map((r) => (["OWN", "CFO", "OE"].includes(r.id) ? Object.assign(r, { branch: "Noida" }) : r));
    draw(noida(), "reporting", { filter: { "pos-f-branch": "Noida" } });
    let drawn = boxes();
    const seatId = (b) => (b.copy ? seatOfCopy(b.id).id : b.id);
    ok("072 AC-46: with a filter, a matching seat still gets its copy under a drawn manager seat",
       drawn.some((b) => b.copy && seatOfCopy(b.id).id === "OE" && b.parent === "CFO"));
    ok("072 AC-46: and nothing is copied under a seat the filter left out", !drawn.some((b) => b.copy && !["OE"].includes(seatOfCopy(b.id).id)));
    const rowsN = noida(), byId = {};
    rowsN.forEach((r) => { byId[r.id] = r; });
    const match = (r) => r.branch === "Noida";
    const above = (id) => rowsN.some((r) => { if (!match(r)) return false; for (let a = byId[r.reports_to], k = 0; a && k < 40; a = byId[a.reports_to], k++) if (a.id === id) return true; return false; });
    ok("072 AC-47: every drawn box is a match or above one", drawn.every((b) => match(byId[seatId(b)]) || above(seatId(b))),
       drawn.filter((b) => !(match(byId[seatId(b)]) || above(seatId(b)))).map((b) => b.id).join(","));
    W.posFocusFirst();
    ok("072 AC-48: the matching line counts seats, not boxes", /^3 matching/.test(doc.getElementById("pos-fline-txt").textContent),
       doc.getElementById("pos-fline-txt").textContent);
    draw(S70(), "reporting", { filter: { "pos-f-role": "Backoffice Executive" } });
    drawn = boxes();
    ok("072 AC-46: a faded seat above a match keeps all its people home",
       drawn.find((b) => b.id === "BO").names.length === 3 && !drawn.some((b) => b.copy));

    // AC-43: the outline, desktop only.
    draw(S70());
    const split = () => [...body().querySelectorAll(".oc-box.pos-split")];
    const ofBO = split().filter((b) => /Back Office<|Back Office$/.test(b.querySelector(".ti").textContent));
    W.posWire();
    W.matchMedia = () => ({ matches: true, addEventListener() {}, addListener() {} });
    ofBO[0].dispatchEvent(new W.MouseEvent("mouseover", { bubbles: true }));
    ok("072 AC-43: pointing at one box of a shared seat outlines its other boxes",
       ofBO.length === 3 && ofBO.slice(1).every((b) => b.classList.contains("rel")) && !ofBO[0].classList.contains("rel")
       && body().querySelectorAll(".oc-box.rel").length === 2);
    ofBO[1].dispatchEvent(new W.FocusEvent("focusin", { bubbles: true }));
    ok("072 AC-43: keyboard focus does the same", ofBO[0].classList.contains("rel") && !ofBO[1].classList.contains("rel"));
    body().querySelector(".oc-box:not(.pos-split)").dispatchEvent(new W.MouseEvent("mouseover", { bubbles: true }));
    ok("072 AC-43: leaving takes the outline away", !body().querySelectorAll(".oc-box.rel").length);
    W.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
    ofBO[0].dispatchEvent(new W.MouseEvent("mouseover", { bubbles: true }));
    ok("072 AC-43: nothing happens on touch", !body().querySelectorAll(".oc-box.rel").length);
  }

  /* 22h. the error state (AC-63) */
  {
    let calls = 0;
    // Only the chart's own call is counted: other panels (066's bell) use gpFetch too.
    W.gpFetch = (m) => { if (/position_table/.test(m)) calls++; return Promise.reject(new Error("Traceback SERVER-SNTL")); };
    await W.posLoad();
    const alert = body().querySelector('[role="alert"]');
    const said = alert ? alert.textContent.replace(/\s+/g, " ").trim() : "";
    ok("072 AC-63: a failed load says what to do, with the code", said === "The chart did not load. Nothing has changed in your seats or your people. "
       + "Check your connection, then try again. If it keeps happening, tell your administrator: code POS-LOAD.Try again", said);
    ok("072 AC-63: never the server's own message", !body().innerHTML.includes("SERVER-SNTL"));
    alert.querySelector("button").click();
    await new Promise((r) => setTimeout(r, 20));
    ok("072 AC-63: Try again loads again", calls === 2);
  }
}

deleteChecks().then(unChecks).then(seats072).then(() => {
  if (problems.length) {
    console.error("positions tree: " + problems.length + " problem(s)");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("positions tree: " + checks + " checks - every seat drawn, "
              + "identical siblings grouped without losing anybody, filters "
              + "show matches with the seats above faded, loops and deep chains survive, a seat is deleted only "
              + "when the server says so, a seat opens its tray, the people "
              + "trays only for HR; slice 072: people under their manager's seat");
  process.exit(0);   // the jsdom window of section 22 would keep Node waiting
});
