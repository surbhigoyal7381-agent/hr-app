/* Drive the combined Objectives & KPIs view in jsdom against a real
   get_performance_tree payload: hierarchy, colour coding, filters, drag and
   drop, and the type-to-search combobox. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(process.argv[2], "utf8");
const tree = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const calls = [];
function apiReply(url, body) {
  const m = /performance_api\.(\w+)|goals_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || "";
  calls.push({ fn, body });
  if (fn === "get_performance_tree") return tree;
  if (fn === "get_performance_context")
    return { employee_id: tree.employee_id, is_hr: !!tree.is_hr, is_manager: true,
             cycles: [{ name: "C1", cycle_name: "Cycle 1", status: "In Progress" }],
             active_cycle: { name: "C1" }, report_count: 2, max_rating: 5 };
  if (fn === "get_linkable_objectives")
    return (tree.flat_goals || []).map(g => ({ ...g, level: "Manager · " + g.employee_name }));
  if (fn === "relink_kpi") return { message: "moved", name: "K", individual_goal: "" };
  if (fn === "get_manageable_employees")
    return [{ name: tree.employee_id, employee_name: "Me", is_self: 1 }];
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => Promise.resolve({
      ok: true, status: 200,
      json: () => Promise.resolve({ message: apiReply(String(url), opts && opts.body) }),
      text: () => Promise.resolve(""),
    });
    w.frappe = { csrf_token: "", call: () => Promise.resolve({ message: [] }) };
    w._version_number = "0";
    w.confirm = () => true;
    w.alert = () => {};
  },
});
const { window } = dom, doc = window.document;

const settle = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  await settle(400);

  // ── Render the tree ────────────────────────────────────────────────
  window.tvLoad();
  await settle(300);

  const body = doc.getElementById("tv-body");
  const goalRows = body.querySelectorAll(".tv-row.tv-goal, .tv-row.tv-goal-org");
  const kpiRows  = body.querySelectorAll(".tv-row.tv-kpi");
  goalRows.length ? ok(`tree rendered ${goalRows.length} objective rows`)
                  : bad("no objective rows rendered");
  kpiRows.length  ? ok(`tree rendered ${kpiRows.length} KPI rows`)
                  : bad("no KPI rows rendered");

  // ── Colour coding is distinct per type ─────────────────────────────
  const cs = el => window.getComputedStyle(el).borderLeftColor;
  const goalColour = goalRows.length ? cs(goalRows[0]) : "";
  const kpiColour  = kpiRows.length ? cs(kpiRows[0]) : "";
  (goalColour && kpiColour && goalColour !== kpiColour)
    ? ok(`left-border colours differ (objective ${goalColour} vs KPI ${kpiColour})`)
    : bad(`left-border colours not distinct: objective=${goalColour} kpi=${kpiColour}`);
  const orgRow = body.querySelector(".tv-row.tv-goal-org");
  orgRow ? ok(`organisational objective has its own colour (${cs(orgRow)})`)
         : bad("no organisational objective row found to colour");

  // ── Nesting: a KPI sits inside its objective's subtree ─────────────
  const nested = body.querySelector(".tv-children .tv-row.tv-kpi");
  nested ? ok("KPIs render nested under their objective")
         : bad("no KPI nested inside .tv-children");

  // ── Drag and drop ──────────────────────────────────────────────────
  const draggable = body.querySelector('.tv-row.tv-kpi[draggable="true"]');
  if (!draggable) { bad("no draggable KPI row"); }
  else {
    ok("KPI rows are draggable");
    const targetRow = body.querySelector(".tv-row[data-drop]");
    const dt = { data: {}, setData(k, v) { this.data[k] = v; }, getData(k) { return this.data[k]; } };
    draggable.dispatchEvent(Object.assign(new window.Event("dragstart", { bubbles: true }), { dataTransfer: dt }));
    draggable.classList.contains("tv-dragging")
      ? ok("dragstart marks the row as dragging") : bad("dragstart did not mark the row");

    const over = Object.assign(new window.Event("dragover", { bubbles: true, cancelable: true }), { dataTransfer: dt });
    targetRow.dispatchEvent(over);
    targetRow.classList.contains("tv-drop-target")
      ? ok("dragover highlights the drop target") : bad("dragover did not highlight the target");

    calls.length = 0;
    targetRow.dispatchEvent(Object.assign(new window.Event("drop", { bubbles: true, cancelable: true }), { dataTransfer: dt }));
    await settle(200);
    const relink = calls.find(c => c.fn === "relink_kpi");
    if (relink) {
      const sent = JSON.parse(relink.body || "{}");
      sent.individual_goal === targetRow.getAttribute("data-drop")
        ? ok(`drop calls relink_kpi with the target objective (${sent.individual_goal})`)
        : bad(`relink_kpi got the wrong objective: ${JSON.stringify(sent)}`);
    } else bad("drop did not call relink_kpi");
  }

  // ── Filters ────────────────────────────────────────────────────────
  calls.length = 0;
  window.tvSetShow("objectives");
  await settle(200);
  let sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
  sent.show === "objectives" ? ok("Objectives filter sends show=objectives")
                             : bad("show filter not sent: " + JSON.stringify(sent));
  const afterObjOnly = doc.getElementById("tv-body").querySelectorAll(".tv-row.tv-kpi").length;
  afterObjOnly === 0 ? ok("Objectives-only hides every KPI row")
                     : bad(`Objectives-only still shows ${afterObjOnly} KPI rows`);

  doc.getElementById("tv-from").value = "2026-01-01";
  doc.getElementById("tv-to").value = "2026-12-31";
  doc.getElementById("tv-category").innerHTML = '<option value="Financial">Financial</option>';
  doc.getElementById("tv-category").value = "Financial";
  calls.length = 0;
  window.tvLoad();
  await settle(200);
  sent = JSON.parse((calls.find(c => c.fn === "get_performance_tree") || {}).body || "{}");
  (sent.date_from === "2026-01-01" && sent.date_to === "2026-12-31" && sent.category === "Financial")
    ? ok("date range and category reach the server")
    : bad("filters not sent: " + JSON.stringify(sent));

  window.tvSetShow("all"); await settle(200);
  window.tvSetView("list"); await settle(200);
  doc.getElementById("tvv-list").classList.contains("active")
    ? ok("view toggles to list") : bad("list view button not active");
  window.tvSetView("tree"); await settle(200);
  doc.getElementById("tv-body").querySelector(".tv-children")
    ? ok("view toggles back to hierarchy") : bad("hierarchy not restored");

  window.tvClearFilters(); await settle(200);
  (!doc.getElementById("tv-from").value && !doc.getElementById("tv-category").value)
    ? ok("Clear resets the filters") : bad("Clear did not reset filters");

  // ── Type-to-search combobox ────────────────────────────────────────
  window.pfOpenKpiModal();
  await settle(300);
  const search = doc.getElementById("pf-k-objective-search");
  const list = doc.getElementById("pf-k-objective-list");
  if (!search || !list) { bad("objective combobox missing"); }
  else {
    const first = (tree.flat_goals || [])[0];
    search.value = (first.goal_name || "").slice(0, 4);
    window.cbxFilter("pf-k-objective");
    const opts = list.querySelectorAll(".cbx-opt");
    opts.length > 1 ? ok(`typing filters objectives (${opts.length - 1} match “${search.value}”)`)
                    : bad("combobox produced no matches for a known prefix");
    search.value = "zzz-no-such-objective";
    window.cbxFilter("pf-k-objective");
    list.querySelector(".cbx-empty") ? ok("combobox reports when nothing matches")
                                     : bad("no empty state for an unmatched search");
    window.cbxPick("pf-k-objective", first.name);
    (doc.getElementById("pf-k-objective").value === first.name &&
     search.value === first.goal_name)
      ? ok("picking sets the hidden id and the visible label")
      : bad(`pick failed: id=${doc.getElementById("pf-k-objective").value} label=${search.value}`);
  }

  // ── Weight units ───────────────────────────────────────────────────
  const units = Array.from(doc.querySelectorAll("#pf-k-unit option")).map(o => o.textContent);
  const weights = ["Grams", "Kilograms", "Quintals", "Tonnes", "Pounds"];
  weights.every(u => units.includes(u))
    ? ok("weight units present: " + weights.join(", "))
    : bad("missing weight units; have: " + units.join(", "));

  console.log(`### tree DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
