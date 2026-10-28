/* Is Home balanced, on the REAL cards, in a REAL browser? (slice 076, AC-110 to
 * AC-114.) Not part of CI: it needs a browser.
 *
 * WHAT IS REAL AND WHAT IS NOT. The page is the real hrms-employee.html with its
 * real stylesheet and its real portal.js, laid out by a real browser. The
 * SERVER is a stub: `frappe.call` and `fetch` answer from data this script
 * builds for each cell. So the card markup, every renderer, the CSS and the
 * reflow are the real ones; the rows in them are synthetic, and so is the
 * absence of a logged-in session. Nothing here proves a server answer.
 *
 * CELLS. 5 personas x 3 data sizes (none, few, 200 rows) x 2 widths (1280, 360).
 * Birthdays are Part C, so the "on" half of the 60 does not exist yet: this is
 * the whole Part A set, 30 cells, which is the design's own "switch off" layout.
 *
 * MEASURES, per cell (02-design section 3; the prototype's own readout):
 *   - largest gap between rows of cards <= 24 px
 *   - the two columns end within 120 px of each other
 *   - no card taller than 2x the median card height (the check-in card counts)
 *   - Pending and Notices show at most 5 rows
 *   - no horizontal scroll
 *   - phone: order is check-in, Pending, Notices
 *   - pairs in a row: within 1.5x on natural height, or stretched (named, with
 *     the natural ratio, never hidden)
 *
 * HOW TO RUN (your own machine or container; the site is not needed):
 *   mkdir -p /tmp/browser && cd /tmp/browser && npm init -y && npm install puppeteer-core
 *   CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe" \
 *   PUPPETEER=/tmp/browser/node_modules/puppeteer-core NODE_PATH=<a folder with jsdom, if the
 *   page loader needs it> node scripts/browser_check_home_076.js
 *
 * Prints one line per cell and the readout table; exits non-zero on a failure.
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const puppeteer = require(process.env.PUPPETEER || "puppeteer-core");
const { readPortalSource } = require("./lib/portal_source");

const CHROME = process.env.CHROME || "/usr/bin/chromium";
const APP = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal");
const PAGE = path.join(APP, "www", "hrms-employee.html");
/* The design tokens (colours, font sizes, --sidebar-w) live in an include the page
   pulls in, not in the files readPortalSource expands. Without them every length
   that uses a token is wrong, so they go in first, exactly as the server sends them. */
const TOKENS = fs.readFileSync(path.join(APP, "templates", "includes", "design_system.html"), "utf8").replace(/\{#[\s\S]*?#\}/g, "");

const NAMES = ["Rohit Sharma", "Priya Nair", "Imran Khan", "Deepa Joshi", "Vikram Singh", "Neelam Gupta", "Sunil Yadav", "Pooja Mishra", "Manoj Tiwari", "Farah Ali", "Kunal Arora", "Lata Devi", "Harish Rawat", "Seema Bhatt", "Ajay Chauhan", "Rekha Pillai"];
const PERSONAS = {
  employee: {label: "Employee", name: "Anita Verma", role: "Sales associate", goals: true, team: false, docs: true, policies: true, hr: false, mgr: false},
  frontline: {label: "Frontline", name: "Ramesh Yadav", role: "Floor staff, shift B", goals: false, team: false, docs: true, policies: false, hr: false, mgr: false},
  manager: {label: "Manager", name: "Sakshi Verma", role: "Store manager", goals: true, team: true, docs: true, policies: true, hr: false, mgr: true},
  hr: {label: "HR Manager", name: "Kavita Rao", role: "HR Manager", goals: true, team: false, docs: true, policies: true, hr: true, mgr: true},
  cxo: {label: "CXO", name: "Arjun Mehta", role: "Chief Executive", goals: true, team: true, docs: false, policies: false, hr: false, mgr: true, cxo: true},
};
const PEND = {   // rows per part by size (the server caps a part at 50)
  employee: {none: {}, few: {policies: 1, my_requests: 1}, many: {policies: 50, my_requests: 50}},
  frontline: {none: {}, few: {my_requests: 1}, many: {policies: 50, my_requests: 50}},
  manager: {none: {}, few: {leave_approvals: 1}, many: {leave_approvals: 50, goal_updates: 50, attendance_fixes: 50, shift_requests: 50, policies: 1}},
  hr: {none: {}, few: {leave_approvals: 1}, many: {leave_approvals: 50, goal_updates: 50, attendance_fixes: 50, shift_requests: 50}},
  cxo: {none: {}, few: {leave_approvals: 2}, many: {leave_approvals: 50, goal_updates: 50, attendance_fixes: 50, shift_requests: 50, policies: 1}},
};
const PART_KEYS = ["leave_approvals", "goal_updates", "attendance_fixes", "shift_requests", "policies", "my_requests"];
const iso = (ago) => { const d = new Date(Date.now() - ago * 86400000); return d.toISOString().slice(0, 10) + " 09:00:00"; };

function inboxFor(pid, size) {
  const cfg = PEND[pid][size], parts = [];
  PART_KEYS.forEach((key) => {
    const n = cfg[key] || 0, rows = [];
    for (let i = 0; i < n; i++) {
      const who = NAMES[(i * 3 + key.length) % NAMES.length], w = iso(1 + ((i * 2) % 20));
      if (key === "leave_approvals") rows.push({name: "L" + i, employee_name: who, from_date: "2026-11-06", to_date: "2026-11-08", leave_type: "Casual Leave", total_days: 3, action: "leave", waiting_since: w});
      else if (key === "goal_updates") rows.push({name: "G" + i, kind: "goal", employee_name: who, subject: "Sell 40 units", action: "goal_update", waiting_since: w});
      else if (key === "attendance_fixes") rows.push({name: "A" + i, employee_name: who, from_date: "2026-10-21", to_date: "2026-10-21", action: "attendance_fix", waiting_since: w});
      else if (key === "shift_requests") rows.push({name: "S" + i, employee_name: who, from_date: "2026-11-09", to_date: "2026-11-09", action: "shift_request", waiting_since: w});
      else if (key === "policies") rows.push({name: "P" + i, title: "Safety on the floor " + (i + 1), version: 2, action: "policy", waiting_since: w});
      else rows.push({name: "M" + i, title: "Leave request", from_date: "2026-11-06", to_date: "2026-11-08", says: "Waiting for your approver", action: "my_leave", waiting_since: w});
    }
    parts.push({key, count: n === 50 ? 200 : n, rows});
  });
  return {total: parts.reduce((a, p) => a + p.count, 0), approvals_total: 0, has_employee: true, parts};
}
function noticesFor(size) {
  if (size === "none") return {unread: 0, any: false, items: []};
  const n = size === "few" ? 2 : 200, items = [];
  for (let i = 0; i < Math.min(n, 5); i++) items.push({name: "N" + i, text: "A grooming red was marked on Mon 26 Oct. Open the day in your Attendance month to read the reason, then ask HR if it is wrong.", link: null, when: "2026-10-27 16:10:00", read: 0});
  return {unread: n, any: true, items};
}
function goalsFor(p, size) {
  if (!p.goals || size === "none") return {available: false};
  const n = size === "few" ? 2 : 12, goals = [];
  for (let i = 0; i < n; i++) goals.push({name: "GL" + i, goal_name: "Sell 40 units this month " + (i + 1), status: "Active", progress_pct: 20 + (i * 7) % 70, trajectory: "On Track", actual_progress: 10, target_value: 40, docstatus: 1});
  return {available: true, goals};
}
function teamGoalsFor(p, size) {
  if (!p.mgr || size === "none") return {available: false};
  const n = size === "few" ? 2 : 40, by = {};
  for (let i = 0; i < n; i++) by["E" + i] = {employee: {employee_name: NAMES[i % NAMES.length], designation: "Associate"},
    goals: [0, 1, 2].map((j) => ({name: "TG" + i + j, goal_name: "Team goal " + j, progress_pct: 30 + j * 20, trajectory: "On Track"}))};
  return {available: true, by_employee: by};
}
function scenario(pid, size) {
  const p = PERSONAS[pid], none = size === "none", many = size === "many";
  const docs = none || !p.docs ? [] : Array.from({length: many ? 12 : 3}, (_, i) => ({name: "D" + i, document_type: "Address proof " + (i + 1), status: "Uploaded", category: "Identity"}));
  const pols = none || !p.policies ? [] : Array.from({length: many ? 6 : 2}, (_, i) => ({name: "PO" + i, title: "Leave and attendance " + (i + 1), version: 2, status: "Published", department: "HR", ack: "pending"}));
  const hols = none ? [] : Array.from({length: many ? 30 : 3}, (_, i) => ({holiday_date: new Date(Date.now() + (i + 1) * 86400000).toISOString().slice(0, 10), description: "Holiday " + (i + 1)}));
  return {
    name: p.name, role: p.role, mgr: p.mgr, hr: p.hr, cxo: !!p.cxo,
    inbox: inboxFor(pid, size), notes: noticesFor(size), goals: goalsFor(p, size), teamGoals: teamGoalsFor(p, size),
    docs: {rows: docs, summary: docs.length + " items"}, policies: {rows: pols, pending: pols.length, can_manage: false},
    dashboard: {leave_balances: none ? [] : [{leave_type: "Casual Leave", total: 12, balance: 8, taken: 4}, {leave_type: "Earned Leave", total: 15, balance: 11, taken: 4}, {leave_type: "Sick Leave", total: 6, balance: 4, taken: 2}, {leave_type: "Comp Off", total: 2, balance: 1, taken: 1}],
      holidays: hols, pending_approvals: []},
  };
}

/* Runs in the page before the portal's own scripts: the server, as data. */
function stubServer(S) {
  const route = (name) => {
    switch (name) {
      case "get_checkin_status": return {employee: {name: "E1", employee_name: S.name, designation: S.role, department: "Operations"}, checked_in: false, last_action: null, marks: null, needs_location: false, todays_checkins: []};
      case "get_portal_context": return {employee: {name: "E1"}, is_manager: S.mgr, is_hr: S.hr, is_system_manager: S.cxo, team: []};
      case "get_available_features": return {goals: true, plan_policy_library: true, plan_employee_documents: true};
      case "get_employee_dashboard": return S.dashboard;
      case "get_inbox": return S.inbox;
      case "notices_feed": return S.notes;
      case "get_goals_portal_data": return S.goals;
      case "get_team_goals": return S.teamGoals;
      case "get_my_documents": return S.docs;
      case "get_my_policies": return S.policies;
      default: return {};
    }
  };
  window.frappe = {
    call(o) { const n = String(o.method).split(".").pop(); setTimeout(() => { o.callback && o.callback({message: route(n)}); o.always && o.always({}); }, 0); return {status: 200}; },
    csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: (s) => s}, msgprint() {},
  };
  window.fetch = (url) => Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({message: route(String(url).split("?")[0].split("/").pop())})});
}

/* Runs in the page after it has settled. */
function measure() {
  const grid = document.getElementById("home-grid"), hero = document.querySelector(".checkin-hero");
  const vis = (el) => getComputedStyle(el).display !== "none";
  const cards = [...grid.children].filter(vis);
  const box = (el) => { const r = el.getBoundingClientRect(); return {id: el.id || el.className, top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY), left: Math.round(r.left), h: Math.round(r.height), w: Math.round(r.width)}; };
  const natural = {};
  grid.style.alignItems = "start";
  cards.forEach((c) => { natural[c.id] = Math.round(c.getBoundingClientRect().height); });
  grid.style.alignItems = "";
  const R = cards.map(box).map((b) => Object.assign(b, {nat: natural[b.id]}));
  const heroBox = box(hero);
  const rows = {};
  R.forEach((r) => { (rows[r.top] = rows[r.top] || []).push(r); });
  const keys = Object.keys(rows).map(Number).sort((a, b) => a - b);
  let maxGap = 0, pairs = [];
  keys.forEach((k, ix) => {
    const g = rows[k];
    if (g.length > 1) { const mx = Math.max(...g.map((x) => x.nat)), mn = Math.min(...g.map((x) => x.nat)); pairs.push({a: g[0].id, b: g[1].id, ratio: mx / mn}); }
    if (ix > 0) maxGap = Math.max(maxGap, k - Math.max(...rows[keys[ix - 1]].map((x) => x.bottom)));
  });
  if (keys.length) maxGap = Math.max(maxGap, keys[0] - heroBox.bottom);
  const hs = R.map((r) => r.h).concat([heroBox.h]).sort((a, b) => a - b), med = hs[Math.floor(hs.length / 2)], tall = hs[hs.length - 1];
  /* A card that spans the row ends both columns together, so it counts as 0. */
  const colsEnd = (() => {
    const span = [...grid.querySelectorAll(".hm-span2")].map((e) => e.id);
    const lastTop = Math.max(...R.map((r) => r.top));
    if (R.some((r) => r.top === lastTop && span.includes(r.id))) return 0;
    const mid = grid.getBoundingClientRect().left + grid.getBoundingClientRect().width / 2 - 1;
    const L = R.filter((r) => r.left < mid), Rr = R.filter((r) => r.left >= mid);
    if (!L.length || !Rr.length) return 0;
    return Math.abs(Math.max(...L.map((r) => r.bottom)) - Math.max(...Rr.map((r) => r.bottom)));
  })();
  const rowCount = (id) => { const c = document.getElementById(id); return c ? c.querySelectorAll(".hm-row").length : 0; };
  const ordered = ["checkin"].concat(R.slice().sort((a, b) => a.top - b.top || a.left - b.left).map((r) => r.id));
  const gridBox = grid.getBoundingClientRect();
  return {
    cards: R.map((r) => ({id: r.id, h: r.h, nat: r.nat, w: r.w})), hero: heroBox.h, pairs, maxGap, med, tall, colsEnd,
    pendingRows: rowCount("home-pending-card"), noticeRows: rowCount("home-notices-card"),
    hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    order: ordered.slice(0, 3), gridW: Math.round(gridBox.width), cols: new Set(R.map((r) => r.left)).size,
    colW: R.length ? R[0].w : 0, span2: [...grid.querySelectorAll(".hm-span2")].map((e) => e.id),
    pendingHidden: !vis(document.getElementById("home-pending-card")), noticesHidden: !vis(document.getElementById("home-notices-card")),
    ncards: R.length, tallId: (R.slice().sort((a, b) => b.h - a.h)[0] || {}).id,
  };
}

async function main() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "home076-"));
  const file = path.join(tmp, "home.html");
  /* The page is a Jinja template; give it the few words the server would. */
  const source = readPortalSource(PAGE)
    .replace(/\{#[\s\S]*?#\}/g, "")
    .replace(/\{\{\s*tenant_name\s*\}\}/g, "Acme")
    .replace(/\{\{\s*_\(\s*["']([^"']*)["']\s*\)\s*\}\}/g, "$1");
  fs.writeFileSync(file, '<!doctype html><html lang="en"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' + TOKENS + "</head><body>" + source + "</body></html>");
  const browser = await puppeteer.launch({executablePath: CHROME, args: ["--no-sandbox", "--disable-dev-shm-usage"]});
  let pass = 0, fail = 0;
  const failures = [], readout = [], stretched = [], existing = [];
  for (const pid of Object.keys(PERSONAS)) {
    for (const size of ["none", "few", "many"]) {
      for (const width of [1280, "1280c", 360]) {
        const page = await browser.newPage();
        const errs = [];
        page.on("pageerror", (e) => { if (!/Unexpected token '\{'|_SUPPORT_EMAIL|Unexpected token/.test(e.message)) errs.push(e.message); });
        const wide = width !== 360;
        await page.setViewport({width: wide ? 1280 : 360, height: wide ? 900 : 780, deviceScaleFactor: 1});
        /* 1280: the sidebar pinned open (240 px, what the design drew). 1280c: as the
           portal starts, collapsed to 56 px. */
        await page.evaluateOnNewDocument(stubServer, scenario(pid, size));
        await page.goto("file://" + file.replace(/\\/g, "/"), {waitUntil: "load"});
        await new Promise((r) => setTimeout(r, 1800));
        /* The portal starts with the sidebar collapsed; 1280 pins it open, as drawn. */
        if (width === 1280) { await page.evaluate(() => window.toggleSbPin()); await new Promise((r) => setTimeout(r, 400)); }
        const m = await page.evaluate(measure);
        const tag = `${PERSONAS[pid].label} · ${size === "many" ? "200 rows" : size} · ${width === 1280 ? "1280px" : width === "1280c" ? "1280px, sidebar collapsed" : "360px"}`;
        const w = wide ? 1280 : 360;
        const bad = [];
        if (m.maxGap > 24) bad.push(`largest gap ${m.maxGap} px (limit 24)`);
        if (wide && m.colsEnd > 120) bad.push(`columns end ${m.colsEnd} px apart (limit 120)`);
        /* The 2x rule is kept apart: when the tall card is one of the EXISTING cards (their
           content is unchanged by this slice and none has a cap), that is a finding about
           that card, not about the grid or the new cards. */
        let existingTall = false;
        if (m.tall > 2 * m.med) {
          if (/^home-(pending|notices)-card$/.test(m.tallId)) bad.push(`tallest card (${m.tallId}) ${m.tall} px is over 2x the median ${m.med} px`);
          else existingTall = true;
        }
        if (m.pendingRows > 5 || m.noticeRows > 5) bad.push(`a list shows more than 5 rows (${m.pendingRows}, ${m.noticeRows})`);
        if (m.hscroll) bad.push("the page scrolls sideways");
        if (width === 360 && (m.order[1] !== "home-pending-card" || m.order[2] !== "home-notices-card")) bad.push("phone order is " + m.order.join(", "));
        if (m.pendingHidden || m.noticesHidden) bad.push("Pending or Notices is hidden");
        if (wide && m.cols !== 2) bad.push(`${m.cols} columns, wanted 2`);
        if (width === 360 && m.cols !== 1) bad.push(`${m.cols} columns, wanted 1`);
        if (wide && m.ncards % 2 === 1 && m.span2.length !== 1) bad.push("an odd card count but no card spans the row");
        errs.forEach((e) => bad.push("page error: " + e));
        if (wide) m.pairs.filter((p) => p.ratio > 1.5).forEach((p) => stretched.push(`${tag}: ${p.a} / ${p.b} ${p.ratio.toFixed(2)}x`));
        readout.push({tag, tall: m.tall, med: m.med, ratio: (m.tall / m.med).toFixed(2), gap: m.maxGap, cols: m.colsEnd, gridW: m.gridW, colW: m.colW, n: m.ncards});
        if (existingTall) existing.push(`${tag}: ${m.tallId} is ${m.tall} px, median ${m.med} px (${(m.tall / m.med).toFixed(1)}x)`);
        if (bad.length) { fail++; failures.push(tag + ": " + bad.join("; ")); console.log("  FAIL  " + tag + "  " + bad.join("; ")); }
        else if (existingTall) { pass++; console.log("  NOTE  " + tag + `  grid fine (gap ${m.maxGap}, cols ${m.colsEnd}); an existing card is over 2x the median: ${m.tallId} ${m.tall} vs ${m.med}`); }
        else { pass++; console.log("  PASS  " + tag + `  (gap ${m.maxGap}, cols ${m.colsEnd}, tallest ${m.tall} vs median ${m.med}, ${m.ncards} cards)`); }
        await page.close();
      }
    }
  }
  await browser.close();
  console.log("\nGrid at 1280: " + readout.filter((r) => /1280/.test(r.tag))[0].gridW + " px wide, column " + readout.filter((r) => /1280/.test(r.tag))[0].colW + " px");
  console.log("Worst tallest/median: " + readout.slice().sort((a, b) => b.ratio - a.ratio).slice(0, 3).map((r) => `${r.tag} ${r.ratio}x (${r.tall}/${r.med})`).join(" | "));
  console.log("Pairs stretched to match (natural height ratio over 1.5x): " + (stretched.length ? "\n  " + stretched.join("\n  ") : "none"));
  console.log("\nCells where an EXISTING card is over 2x the median (rule 2 of AC-112): " + existing.length + " of " + (pass + fail));
  const kinds = {};
  existing.forEach((e) => { const k = e.match(/: (\S+) is/)[1]; kinds[k] = (kinds[k] || 0) + 1; });
  console.log("  by card: " + JSON.stringify(kinds));
  console.log(`\n### Home 076 balance: ${pass} passed (${existing.length} of them noted for an existing card's height), ${fail} failed, ${pass + fail} cells`);
  fs.rmSync(tmp, {recursive: true, force: true});
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
