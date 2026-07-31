/* The redesigned Objectives & KPIs view: search, filter chips, popovers,
   expand/collapse, floating toast, empty states, keyboard shortcut. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(process.argv[2], "utf8");
const tree = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const calls = [];
let _treeOverride = null;
const setTreeOverride = t => { _treeOverride = t; };
function reply(url, body) {
  const m = /performance_api\.(\w+)|goals_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || "";
  calls.push({ fn, body });
  if (fn === "get_performance_tree") return _treeOverride || tree;
  if (fn === "get_performance_context")
    return { employee_id: tree.employee_id, is_hr: !!tree.is_hr, is_manager: true,
             cycles: [
               { name: "C1", cycle_name: "H2 2026 Performance Cycle", status: "In Progress" },
               { name: "C2", cycle_name: "Mid-Year 2026 Performance Cycle", status: "Not Started" },
             ],
             active_cycle: { name: "C1" }, report_count: 2, max_rating: 5 };
  if (fn === "get_portal_context")
    return { employee_id: tree.employee_id, employee_name: "Tester", is_manager: true,
             goals_installed: true, dashboard: {}, cycle: null };
  if (fn === "relink_kpi") return { message: "'X' moved to Y", name: "K", individual_goal: "" };
  if (fn === "list_appraisals") return { appraisals: [], is_hr: 1, employee_id: "E", counts: {} };
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
    w.frappe = { csrf_token: "", call: () => Promise.resolve({ message: [] }) };
    w._version_number = "0"; w.confirm = () => true; w.alert = () => {};
  },
});
const { window } = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const vis = el => el && window.getComputedStyle(el).display !== "none" && !el.hidden;

(async () => {
  await settle(400);
  // Go through the real panel entry point so pfBoot runs and the cycle
  // pickers get populated the way they do in the app.
  window.switchPanel("goals");
  await settle(300);
  window.gpShowTab("tree");
  window.tvLoad();
  await settle(300);

  const body = doc.getElementById("tv-body");
  const firstGoal = (tree.flat_goals || [])[0];
  const allRows = () => body.querySelectorAll(".tv-row").length;

  // ── The control bar is actually rendered, not merely present ───────
  // A class-name collision once styled the whole toolbar as a 64x5px
  // progress pill with overflow:hidden: every control existed in the DOM
  // and none of them were visible. Assert real geometry, not presence.
  const bar = doc.querySelector(".tv-controls");
  if (!bar) { bad("control bar missing from the DOM"); }
  else {
    const bs = window.getComputedStyle(bar);
    const collapsed = bs.overflow === "hidden" &&
                      /^\d+(\.\d+)?px$/.test(bs.height) && parseFloat(bs.height) < 20;
    !collapsed ? ok(`control bar is not collapsed (height:${bs.height || "auto"} overflow:${bs.overflow || "visible"})`)
               : bad(`control bar collapsed to height:${bs.height} overflow:${bs.overflow}`);
    bs.position === "sticky" ? ok("control bar is sticky") : bad("control bar lost its sticky position: " + bs.position);
  }
  // Every control the bar owns must be a descendant of it and not clipped away.
  ["tv-search", "tvf-all", "tvv-tree", "tv-filter-btn", "tv-new-btn"].forEach(function (id) {
    const el = doc.getElementById(id);
    if (!el) { bad(`control #${id} missing`); return; }
    if (!bar || !bar.contains(el)) { bad(`control #${id} is not inside the control bar`); return; }
    const cs = window.getComputedStyle(el);
    cs.display !== "none" && cs.visibility !== "hidden"
      ? ok(`control #${id} is visible`)
      : bad(`control #${id} hidden (display:${cs.display} visibility:${cs.visibility})`);
  });

  // ── The right-hand cluster lines up down the page ──────────────────
  // Rows carry a different number of action buttons, and .tv-acts occupies
  // space even while faded out, so intrinsic widths put the bar and % in a
  // different column on every row. Each part must have a fixed basis.
  {
    const rows = Array.from(body.querySelectorAll(".tv-row"));
    const widthsOf = sel => rows.map(r => {
      const el = r.querySelector(sel);
      return el ? window.getComputedStyle(el).width : null;
    }).filter(Boolean);

    [[".tv-bar", "progress bar"], [".tv-pct", "percentage"], [".tv-acts", "actions"]]
      .forEach(([sel, label]) => {
        const w = widthsOf(sel);
        const unique = Array.from(new Set(w));
        if (!w.length) { bad(`no ${label} found to measure`); return; }
        unique.length === 1 && /^\d+px$/.test(unique[0])
          ? ok(`${label} has one fixed width across all ${w.length} rows (${unique[0]})`)
          : bad(`${label} width varies by row: ${unique.join(", ")}`);
      });

    // Differing button counts must not change the column layout.
    const actCounts = Array.from(new Set(rows.map(r => r.querySelectorAll(".tv-acts .tv-icon").length)));
    actCounts.length > 1
      ? ok(`rows do differ in action count (${actCounts.sort().join(" vs ")}) yet still align`)
      : ok("action counts uniform in this dataset");
  }

  // ── Search ─────────────────────────────────────────────────────────
  const box = doc.getElementById("tv-search");
  box ? ok("search box present") : bad("no search box");
  const before = allRows();
  const term = (firstGoal.goal_name || "").slice(0, 6);
  box.value = term;
  window.tvSearch();
  await settle(80);
  const after = allRows();
  after < before ? ok(`search narrows the tree (${before} → ${after} rows for “${term}”)`)
                 : bad(`search did not narrow: ${before} → ${after}`);
  body.querySelector("mark") ? ok("matches are highlighted in place")
                             : bad("no <mark> highlight on a match");
  body.querySelector(".tv-row.tv-hit") ? ok("matching rows are visually flagged")
                                       : bad("no .tv-hit on a matching row");
  doc.querySelector(".tv-search.has-value")
    ? ok("clear affordance appears once typing") : bad("clear button did not appear");

  // Ancestors of a deep match stay visible so hierarchy is not lost.
  const deep = (tree.flat_goals || []).find(g => g.parent_goal);
  if (deep) {
    box.value = (deep.goal_name || "").slice(0, 6);
    window.tvSearch();
    await settle(80);
    const names = body.textContent;
    const parent = (tree.flat_goals || []).find(g => g.name === deep.parent_goal);
    (parent && names.includes(parent.goal_name.slice(0, 6)))
      ? ok("ancestors of a deep match stay visible")
      : bad("a deep match lost its parent chain");
  }

  // No-match state offers the way out.
  box.value = "zzzz-nothing";
  window.tvSearch();
  await settle(80);
  body.textContent.includes("Nothing matches")
    ? ok("no-match empty state names the query") : bad("no distinct no-match state");
  body.querySelector("button")
    ? ok("no-match state offers Clear search") : bad("no escape from the no-match state");

  window.tvClearSearch();
  await settle(80);
  allRows() === before ? ok("clearing search restores every row")
                       : bad(`after clear: ${allRows()} rows, expected ${before}`);

  // "/" focuses search from anywhere on the page.
  doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "/", bubbles: true }));
  await settle(40);
  doc.activeElement === box ? ok("“/” focuses the search box")
                            : bad("“/” did not focus search");

  // ── Filters popover + chips ────────────────────────────────────────
  const pop = doc.getElementById("tv-pop");
  vis(pop) === false ? ok("filters start collapsed, so the tree leads")
                     : bad("filter popover is open by default");
  window.tvTogglePop();
  vis(pop) ? ok("Filters opens the popover") : bad("popover did not open");
  doc.getElementById("tv-filter-btn").getAttribute("aria-expanded") === "true"
    ? ok("popover reports aria-expanded") : bad("aria-expanded not set");

  // The sticky control bar is a stacking context (position:sticky + z-index),
  // so an overlay left inside it can never paint above the sidebar whatever
  // z-index it carries. It has to be portaled out and outrank the sidebar.
  {
    const sidebarZ = (() => {
      const sb = doc.querySelector(".sidebar");
      return sb ? parseInt(window.getComputedStyle(sb).zIndex, 10) || 0 : 0;
    })();
    const popZ = parseInt(window.getComputedStyle(pop).zIndex, 10) || 0;
    const bar = doc.querySelector(".tv-controls");

    pop.parentNode === doc.body
      ? ok("filter popover is portaled to <body>, escaping the sticky bar's stacking context")
      : bad(`popover still nested in ${pop.parentNode.className || pop.parentNode.tagName} — it will render under the sidebar`);
    !(bar && bar.contains(pop))
      ? ok("popover is not a descendant of the sticky control bar") : bad("popover still inside .tv-controls");
    popZ > sidebarZ
      ? ok(`popover z-index ${popZ} outranks the sidebar's ${sidebarZ}`)
      : bad(`popover z-index ${popZ} does not clear the sidebar's ${sidebarZ}`);
    window.getComputedStyle(pop).position === "fixed"
      ? ok("popover is positioned fixed against the viewport")
      : bad("popover is not fixed: " + window.getComputedStyle(pop).position);

    // Closing must still work now that "outside" is measured differently.
    doc.body.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    await settle(40);
    !pop.classList.contains("open")
      ? ok("clicking outside still closes the portaled popover")
      : bad("popover no longer closes on an outside click");
    window.tvTogglePop();
    await settle(40);
    // A click inside must NOT close it.
    const inner = pop.querySelector("select, input");
    if (inner) {
      inner.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
      await settle(40);
      pop.classList.contains("open")
        ? ok("clicking inside the popover keeps it open")
        : bad("clicking a field inside the popover closed it");
    }
    // The New menu shares the same treatment.
    window.tvToggleNew();
    const nm = doc.getElementById("tv-new-menu");
    (nm.parentNode === doc.body && (parseInt(window.getComputedStyle(nm).zIndex, 10) || 0) > sidebarZ)
      ? ok("New menu is portaled and outranks the sidebar too")
      : bad("New menu still trapped in the control bar");
    window.tvCloseNew();
    window.tvTogglePop();
  }

  doc.getElementById("tv-from").value = "2026-01-01";
  doc.getElementById("tv-to").value = "2026-12-31";
  window.tvLoad();
  await settle(200);
  const chips = doc.getElementById("tv-chips");
  (!chips.hidden && chips.textContent.includes("Period"))
    ? ok("an active filter shows as a removable chip") : bad("no chip for the date filter");
  const badge = doc.getElementById("tv-filter-count");
  const chipCount = chips.querySelectorAll(".tv-chip").length;
  (!badge.hidden && badge.textContent === String(chipCount) && chipCount > 0)
    ? ok(`Filters badge matches the active filters (${chipCount})`)
    : bad(`badge "${badge.textContent}" (hidden=${badge.hidden}) vs ${chipCount} chips`);

  calls.length = 0;
  window.tvChipClear("dates");
  await settle(200);
  (!doc.getElementById("tv-from").value && calls.some(c => c.fn === "get_performance_tree"))
    ? ok("dismissing a chip clears that filter and reloads")
    : bad("chip dismissal did not clear the filter");

  // ── Appraisal cycle is a usable filter ─────────────────────────────
  {
    const cy = doc.getElementById("tv-cycle");
    const popEl = doc.getElementById("tv-pop");
    if (!cy) { bad("no cycle filter"); }
    else {
      popEl && popEl.contains(cy) ? ok("appraisal cycle sits in the filter dialog")
                                  : bad("cycle filter is not inside the filter dialog");
      const opts = Array.from(cy.options);
      opts.length > 1 ? ok(`cycle filter is populated (${opts.length} options)`)
                      : bad(`cycle filter has ${opts.length} option(s): ${opts.map(o => o.text)}`);
      // Without an "all" option the filter can be set but never cleared.
      opts.some(o => o.value === "")
        ? ok("cycle filter offers “All cycles” so it can be cleared")
        : bad("cycle filter has no all-cycles option — it cannot be cleared");
      opts.some(o => /·/.test(o.text))
        ? ok("cycle options show their status") : bad("cycle options missing status");

      // Choosing a cycle must reach the server and raise a chip.
      const real = opts.find(o => o.value);
      cy.value = real.value;
      calls.length = 0;
      window.tvLoad();
      await settle(200);
      const sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
      sent.cycle === real.value ? ok("selecting a cycle filters server-side")
                                : bad("cycle not sent: " + JSON.stringify(sent));
      doc.getElementById("tv-chips").textContent.includes("Cycle")
        ? ok("the chosen cycle shows as a chip") : bad("no chip for the cycle filter");

      // And dismissing that chip must actually return to All cycles.
      window.tvChipClear("cycle");
      await settle(200);
      cy.value === "" ? ok("dismissing the cycle chip returns to All cycles")
                      : bad(`cycle chip dismissal left value "${cy.value}"`);
    }

    // The dialog has to be wide enough for a full cycle name.
    if (popEl) {
      const w = parseFloat(window.getComputedStyle(popEl).width);
      w >= 380 ? ok(`filter dialog is wide enough (${w}px)`)
               : bad(`filter dialog only ${w}px — long cycle names will truncate`);
    }
  }

  // ── Scope: just me / department / organisation ─────────────────────
  {
    const sc = doc.getElementById("tv-scope");
    if (!sc) { bad("no scope selector"); }
    else {
      const vals = Array.from(sc.options).map(o => o.value);
      ["mine", "department", "organisation"].every(v => vals.includes(v))
        ? ok(`scope offers ${vals.join(", ")}`)
        : bad("scope missing an option; has " + vals.join(", "));

      for (const want of ["mine", "department", "organisation"]) {
        sc.value = want;
        calls.length = 0;
        window.tvLoad();
        await settle(150);
        const sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
        sent.scope === want ? ok(`scope “${want}” reaches the server`)
                            : bad(`scope ${want} not sent: ${JSON.stringify(sent)}`);
      }
      doc.getElementById("tv-chips").textContent.includes("Scope")
        ? ok("a non-default scope shows as a chip") : bad("no chip for scope");
      window.tvChipClear("scope");
      await settle(150);
      sc.value === "team" ? ok("dismissing the scope chip returns to the default")
                          : bad(`scope chip dismissal left "${sc.value}"`);
    }
  }

  // ── Trajectory and progress filters ────────────────────────────────
  {
    const boxes = Array.from(doc.querySelectorAll(".tv-traj-cb"));
    boxes.length >= 3 ? ok(`status filter offers ${boxes.map(b => b.value).join(", ")}`)
                      : bad(`only ${boxes.length} status options`);
    boxes.filter(b => ["On Track", "At Risk", "Off Track"].includes(b.value)).length === 3
      ? ok("on track / at risk / off track all present")
      : bad("missing one of the three trajectories");

    boxes.find(b => b.value === "At Risk").checked = true;
    boxes.find(b => b.value === "Off Track").checked = true;
    calls.length = 0;
    window.tvLoad();
    await settle(150);
    let sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
    sent.trajectory === "At Risk,Off Track"
      ? ok("multiple statuses combine into one filter")
      : bad("trajectory not sent as expected: " + JSON.stringify(sent.trajectory));
    doc.getElementById("tv-chips").textContent.includes("At Risk")
      ? ok("status selection shows as a chip") : bad("no chip for status");
    window.tvChipClear("trajectory");
    await settle(150);
    boxes.every(b => !b.checked) ? ok("dismissing the status chip clears every box")
                                 : bad("status chip dismissal left boxes checked");

    doc.getElementById("tv-prog-min").value = "40";
    doc.getElementById("tv-prog-max").value = "80";
    calls.length = 0;
    window.tvLoad();
    await settle(150);
    sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
    (sent.progress_min === "40" && sent.progress_max === "80")
      ? ok("progress range reaches the server")
      : bad("progress range not sent: " + JSON.stringify(sent));
    doc.getElementById("tv-chips").textContent.includes("40–80%")
      ? ok("progress range shows as a chip") : bad("no chip for progress range");
    window.tvChipClear("progress");
    await settle(150);
    (!doc.getElementById("tv-prog-min").value && !doc.getElementById("tv-prog-max").value)
      ? ok("dismissing the progress chip clears both bounds")
      : bad("progress chip dismissal left a bound set");
  }

  // ── Context ancestors are shown as scaffolding, not results ────────
  {
    const withCtx = JSON.parse(JSON.stringify(tree));
    if (withCtx.roots && withCtx.roots.length) {
      withCtx.roots[0].context = 1;
      const original = _treeOverride;
      setTreeOverride(withCtx);
      window.tvLoad();
      await settle(200);
      const row = doc.querySelector("#tv-body .tv-row.tv-context");
      row ? ok("ancestors kept for cascade are visually distinguished")
          : bad("context ancestor renders identically to a matched row");
      row && row.textContent.toLowerCase().includes("context")
        ? ok("context rows are labelled, so the filter is not misread")
        : bad("context row carries no label");
      setTreeOverride(original);
      window.tvLoad();
      await settle(200);
    }
  }

  // ── Overdue and cycle membership are visible on the row ────────────
  {
    const marked = JSON.parse(JSON.stringify(tree));
    const firstRoot = marked.roots && marked.roots[0];
    if (firstRoot) {
      firstRoot.is_overdue = 1;
      firstRoot.in_cycle = "H2 2026";
      const kpi = (firstRoot.kpis && firstRoot.kpis[0]) ||
                  (firstRoot.children && firstRoot.children[0] && firstRoot.children[0].kpis[0]);
      if (kpi) { kpi.is_overdue = 1; kpi.in_cycle = ""; }

      setTreeOverride(marked);
      window.tvLoad();
      await settle(250);

      const body2 = doc.getElementById("tv-body");
      body2.querySelector(".tv-row.tv-overdue")
        ? ok("a passed deadline is highlighted on the row") : bad("no overdue highlight");
      body2.querySelector(".tv-overdue-tag")
        ? ok("overdue rows carry an explicit label") : bad("overdue row has no label");
      body2.querySelector(".tv-incycle")
        ? ok("items already in the review are marked") : bad("no in-review marker");

      // Everyone can nominate, so the control is not gated on can_edit.
      const cycleBtns = body2.querySelectorAll('.tv-icon[aria-label="Toggle review cycle"]');
      cycleBtns.length
        ? ok(`every row offers a consider-in-cycle toggle (${cycleBtns.length})`)
        : bad("no cycle toggle on any row");

      calls.length = 0;
      cycleBtns[0].dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
      await settle(200);
      const call = calls.find(c => c.fn === "set_cycle_membership");
      if (call) {
        const sent = JSON.parse(call.body || "{}");
        (sent.kind && sent.name && sent.cycle !== undefined)
          ? ok(`toggling posts set_cycle_membership (${sent.kind}, include=${sent.include})`)
          : bad("bad membership payload: " + JSON.stringify(sent));
      } else bad("cycle toggle did not call set_cycle_membership");

      setTreeOverride(null);
      window.tvLoad();
      await settle(200);
    }
  }

  // ── New menu ───────────────────────────────────────────────────────
  const menu = doc.getElementById("tv-new-menu");
  vis(menu) === false ? ok("New menu starts closed") : bad("New menu open by default");
  window.tvToggleNew();
  vis(menu) ? ok("New opens a menu offering Objective and KPI")
            : bad("New menu did not open");
  (menu.textContent.includes("Objective") && menu.textContent.includes("KPI"))
    ? ok("New menu explains what each type is for") : bad("New menu missing descriptions");
  window.tvCloseNew();

  // ── Expand / collapse all ──────────────────────────────────────────
  window.tvExpandAll(false);
  await settle(80);
  const collapsed = body.querySelectorAll(".tv-children").length;
  window.tvExpandAll(true);
  await settle(80);
  const expanded = body.querySelectorAll(".tv-children").length;
  expanded > collapsed ? ok(`expand/collapse all works (${collapsed} → ${expanded} groups)`)
                       : bad(`collapse/expand had no effect: ${collapsed} vs ${expanded}`);

  // ── Toast floats instead of shifting the page ──────────────────────
  window.tvToast("ok", "Moved", true);
  const toast = doc.getElementById("tv-msg");
  const pos = window.getComputedStyle(toast).position;
  (!toast.hidden && pos === "fixed")
    ? ok(`feedback floats over the page (position:${pos})`)
    : bad(`toast is not fixed: hidden=${toast.hidden} position=${pos}`);
  toast.getAttribute("role") === "status"
    ? ok("toast is announced to assistive tech") : bad("toast has no aria role");

  // ── Accessibility of the tree rows ─────────────────────────────────
  body.querySelector('[role="treeitem"]') ? ok("rows expose role=treeitem")
                                          : bad("rows have no tree semantics");
  const caret = body.querySelector(".tv-caret[aria-expanded]");
  caret ? ok("carets expose aria-expanded") : bad("carets missing aria-expanded");
  const iconBtn = body.querySelector(".tv-icon[aria-label]");
  iconBtn ? ok("icon-only actions carry aria-labels") : bad("icon buttons have no labels");

  console.log(`### redesign test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
