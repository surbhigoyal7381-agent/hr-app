/* Slice 045, Wave 4: the Growth and Team panels, driven in a real DOM.
 *
 * **This file replaces `portal_appraisal_test.js`**, which drove
 * `#panel-appraisals` - a panel the page has not had for a long time. It had
 * never run, so nobody found out. 045 AC-64 offered two honest endings: drive a
 * panel that exists, or delete it in a commit that says why. This is the first
 * one: the same subject (an employee's review), against the screen that
 * actually exists now.
 *
 * Same method as `next_time_pay_test.js`: load the preview page's own source -
 * markup, stylesheets and scripts, expanded the way the server serves them -
 * put it in jsdom, answer the calls with a fixture, then look at what a PERSON
 * would see.
 *
 * **What this file cannot do, said plainly.** jsdom has no layout, so it cannot
 * measure a 44px button or find a sideways scroll, and it is kinder than a
 * browser about failed calls. Those go through
 * `scripts/browser_check_growth_team.js`, which drives Chromium at 390px
 * against real records.
 *
 * The hostile string is a job title and a company value's name. Both are free
 * text somebody in HR can really type, so this is a stored-XSS shape rather
 * than a theoretical one.
 *
 * Run through scripts/run_dom_tests.js, which is what CI runs.
 */

const { JSDOM, VirtualConsole } = require("jsdom");
const { readPreviewSource } = require("../../scripts/lib/portal_source");

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log("  PASS  " + m); };
const bad = (m) => { fail++; console.log("  FAIL  " + m); };
const is = (got, want, m) =>
  (String(got) === String(want) ? ok(m)
    : bad(m + "  (got " + JSON.stringify(got) + ", wanted " + JSON.stringify(want) + ")"));

const NASTY = '<img src=x onerror=alert(1)>';

function fillTemplate(src) {
  return src
    .replace(/\{%\s*extends[^%]*%\}/g, "")
    .replace(/\{%\s*block [a-z_]+\s*%\}/g, "")
    .replace(/\{%\s*endblock\s*%\}/g, "")
    .replace(/\{%\s*include[^%]*%\}/g, "")
    .replace(/\{#[\s\S]*?#\}/g, "")
    .replace(/\{\{\s*tenant_name\s*\|\s*tojson\s*\}\}/g, '"Test Tenant"')
    .replace(/\{\{\s*tenant_name\[0\]\s*\|\s*upper\s*\}\}/g, "T")
    .replace(/\{\{\s*tenant_name\s*\}\}/g, "Test Tenant")
    .replace(/\{\{\s*asset_version\s*\|\s*e\s*\}\}/g, "1")
    .replace(/\{\{\s*brand_mark_url\s*\|\s*e\s*\}\}/g, "")
    .replace(/\{%\s*if brand_mark_url\s*%\}[\s\S]*?\{%\s*endif\s*%\}/g, "")
    .replace(/\{\{\s*_\("([^"]*)"\)\s*\}\}/g, "$1");
}

const SRC = fillTemplate(readPreviewSource());

const TEAM = "alvoraa_portal.team_api.get_team";
const GROWTH = "alvoraa_portal.growth_api.get_growth";
const REVIEW = "alvoraa_portal.growth_api.get_self_review";
const SAVE = "alvoraa_portal.growth_api.save_self_review";

function makeFrame(over) {
  return Object.assign({
    user: "sandeep@example.com",
    user_full_name: "Sandeep Gupta",
    has_employee: true,
    me: { employee: "HR-EMP-1", employee_name: "Sandeep Gupta",
          designation: "Store Manager", department: "Retail", image: null,
          company: "Test Co" },
    is_hr: false, is_manager: true, is_system_manager: false,
    is_control_plane: false, has_reports: true, scope_is_store: false,
    may_save_settings: false, review_open_count: null,
    features: { goals: 1, expenses: 1 },
    switch_target: null, persona_rule: 3, show_team: true,
    allowed_pages: ["home", "inbox", "time", "growth", "pay", "team"],
    bottom_bar: ["home", "inbox", "team", "growth"],
  }, over || {});
}

function makeCounts(over) {
  return Object.assign({
    total: 0, approvals_total: 0, has_employee: true, parts: [],
    corrections_hr_scope: false,
  }, over || {});
}

/* One Team row, in the shape `team_api.get_team` really returns. The same key
   set, so a test cannot pass against a shape the server does not send. */
function row(name, employee_name, actions, over) {
  return Object.assign({
    name: name, employee_name: employee_name, designation: "Sales Executive",
    department: "Retail", user_id: null, image: null,
    basis: "direct", also_covered: false, actions: actions,
  }, over || {});
}

const MANAGER_ACTIONS = ["approve_correction", "approve_evidence",
                         "approve_leave", "open_record", "see_leave_why",
                         "see_presence", "see_scorecard", "set_goals"];
const COVERED_ACTIONS = ["act_as_hr", "approve_correction", "cancel_deduction",
                         "invite_or_block_phone", "open_record", "see_presence"];
/* The both-person: the manager column PLUS the HR-only column, on one row,
   drawn once, under "Your team" (AC-75). */
const BOTH_ACTIONS = MANAGER_ACTIONS.concat(
  ["act_as_hr", "cancel_deduction", "invite_or_block_phone"]).sort();

function makeTeam(over) {
  return Object.assign({
    me: { employee: "HR-EMP-1", employee_name: "Sandeep Gupta",
          designation: "Store Manager", department: "Retail", image: null,
          company: "Test Co" },
    direct: {
      rows: [row("HR-EMP-2", "Anita Sharma", MANAGER_ACTIONS),
             row("HR-EMP-3", "Rahul Verma", MANAGER_ACTIONS)],
      total: 2, capped: false, cap: 50,
    },
    covered: null,
    is_hr_scope: false, has_direct: true, has_covered: false,
  }, over || {});
}

function makeGrowth(over) {
  return Object.assign({
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma",
          designation: "Sales Executive", department: "Retail", image: null,
          company: "Test Co" },
    cycle: { name: "C1", cycle_name: "H2 2026", start_date: "2026-07-01",
             end_date: "2026-12-31" },
    goals: [{
      goal: "IG-1", goal_name: "Grow counter sales", unit: "Lakh",
      target: 100, approved: 28.4, progress_pct: 28, status: "In Progress",
      start_date: "2026-07-01", end_date: "2026-12-31", is_extra_initiative: 0,
      trajectory: { state: "At Risk", as_of: "2026-09-10", stale: false,
                    needs_attention: true },
      waiting: [],
      kpis: [{ kpi: "K-1", kpi_name: "Counter sales", unit: "Lakh",
               target: 100, approved: 28.4, attainment_pct: 28,
               /* The one AC-29 is written about: 28.4 approved, 3.1 waiting,
                  and 31.5 nowhere. */
               waiting: [{ amount: 3.1, logged_on: "2026-09-10",
                           logged_by: "Sakshi Verma" }] }],
    }, {
      goal: "IG-2", goal_name: "Train two juniors", unit: "",
      target: null, approved: null, progress_pct: null, status: "In Progress",
      start_date: "2026-07-01", end_date: "2026-12-31", is_extra_initiative: 0,
      /* No trajectory at all: "Not set yet", never "Off Track", never 0 %. */
      trajectory: { state: "", as_of: "", stale: true, needs_attention: false },
      waiting: [], kpis: [],
    }],
    needs_attention: ["IG-1"],
    review: { appraisal: "AP-1", status: "Employee Review",
              goes_to: "Sakshi Verma", has_manager: true, can_open: true },
    stale_after_days: 14,
  }, over || {});
}

/* SEVEN values, because five would let an implementation that assumed five
   pass. Surbhi's answer was all of them. */
function makeReview(over) {
  const values = [];
  for (let i = 1; i <= 7; i++) {
    values.push({ name: "CV-" + i, value_name: "Value " + i,
                  icon_emoji: "", description: "What Value " + i + " means" });
  }
  return Object.assign({
    appraisal: "AP-1",
    cycle: { name: "C1", cycle_name: "H2 2026", start_date: "2026-07-01",
             end_date: "2026-12-31" },
    review_status: "Employee Review",
    goals: [{ name: "RI-1", goal_name: "Grow counter sales", unit: "Lakh",
              target_value: 100, actual_progress: 28.4 }],
    standalone_kpis: [],
    values: values, values_count: 7,
    answers: {}, steps: ["goals", "values", "open_items", "next", "overall"],
    steps_answered: [],
    rating_min: 1, rating_max: 5, rating_step: 1,
    budget_bytes: 63487, used_bytes: 2,
  }, over || {});
}

function reply(status, payload) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status: status,
    statusText: String(status),
    text: () => Promise.resolve(JSON.stringify(payload)),
  });
}

function said(sentence) {
  return JSON.stringify([JSON.stringify({ message: sentence })]);
}

function load(hash, frame, counts, answers) {
  answers = answers || {};
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => {
    if (!/Not implemented: navigation/.test(e.message)) { console.error(e.message); }
  });
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" + SRC + "</body></html>",
    {
      runScripts: "dangerously",
      pretendToBeVisual: true,
      virtualConsole: vc,
      url: "http://test.localhost/hrms-employee-next" + (hash || ""),
      beforeParse(w) {
        w.calls = [];
        w.sent = [];
        w.frappe = { _: (s) => s, csrf_token: "token-the-page-was-built-with" };
        w.document.cookie = "user_id=sandeep@example.com";
        w.alert = () => { w.__alerted = true; };
        w.__alerted = false;

        w.fetch = (url, opts) => {
          url = String(url);
          if (url.indexOf("/api/method/") !== 0) {
            return Promise.resolve({
              ok: true, status: 200, statusText: "OK",
              text: () => Promise.resolve(
                '<script>frappe.csrf_token = "a-fresh-token"</script>'),
            });
          }
          const method = url.slice("/api/method/".length);
          w.calls.push(method);
          const args = opts && opts.body ? JSON.parse(opts.body) : {};
          w.sent.push({ method: method, args: args });
          const custom = answers[method];
          if (custom && custom.refuse) {
            return reply(403, { exc_type: "PermissionError",
                                _server_messages: said(custom.refuse) });
          }
          if (typeof custom === "function") { return reply(200, { message: custom(args) }); }
          let message = null;
          if (method.endsWith("get_frame")) { message = frame; }
          else if (method.endsWith("get_nav_counts")) { message = counts; }
          else { message = custom === undefined ? { rows: [] } : custom; }
          return reply(200, { message: message });
        };
      },
    });
  return new Promise((resolve) => {
    setTimeout(() => setTimeout(() => setTimeout(() => setTimeout(
      () => setTimeout(() => resolve(dom), 0), 0), 0), 0), 0);
  });
}

const el = (dom, id) => dom.window.document.getElementById(id);
const screens = (dom) => el(dom, "nf-screens");
const kind = (dom) => el(dom, "nf-state").hidden ? null : el(dom, "nf-state").getAttribute("data-kind");
const text = (dom) => screens(dom).textContent;
const sheetText = (dom) => el(dom, "nf-sheet-body").textContent;
const sheetOpen = (dom) => !el(dom, "nf-sheet-wrap").hidden;
const settle = () => new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
const headings = (dom) =>
  Array.from(screens(dom).querySelectorAll(".nf-card-title")).map((n) => n.textContent);

async function run() {

  /* ── the panels registered themselves ────────────────────────────────── */

  let dom = await load("#team", makeFrame(), makeCounts(), { [TEAM]: makeTeam() });
  is(dom.window.NextFrame.hasPanel("team"), true, "the Team panel registered itself");
  is(dom.window.NextFrame.hasPanel("growth"), true, "the Growth panel registered itself");
  is(dom.window.NextFrame.hasPanel("growth/review"), true,
     "and so did the self-review wizard");

  /* ── Team: two sections, never one list with a label ─────────────────── */

  is(kind(dom), null, "Team is not showing an error or a spinner");
  is(headings(dom).some((h) => h.indexOf("Your team") === 0), true,
     "a manager's screen draws Your team");
  is(text(dom).indexOf("You cover"), -1,
     "AC-73: a manager who is not HR never sees the second heading - it is " +
     "absent from the markup, not hidden by CSS");
  is(headings(dom).find((h) => h.indexOf("Your team") === 0), "Your team (2)",
     "the count is in the heading");
  is(screens(dom).querySelectorAll(".nf-person").length, 2,
     "and it equals the number of rows drawn beneath it");

  /* Store HR with no reports: the other way round. */
  dom = await load("#team", makeFrame({ is_hr: true, has_reports: false }),
                   makeCounts(), {
    [TEAM]: Object.assign(makeTeam(), {
      direct: { rows: [], total: 0, capped: false, cap: 50 },
      covered: { rows: [row("HR-EMP-9", "Deepak Rana", COVERED_ACTIONS,
                            { basis: "covered", also_covered: true })],
                 total: 38, capped: true, cap: 50 },
      is_hr_scope: true, has_direct: false, has_covered: true }),
  });
  is(text(dom).indexOf("Your team"), -1,
     "AC-73: store HR with no reports never sees an empty Your team heading");
  is(headings(dom).some((h) => h.indexOf("You cover") === 0), true,
     "she sees You cover");
  is(headings(dom).find((h) => h.indexOf("You cover") === 0),
     "You cover — showing the first 1 of 38",
     "AC-74: a capped section says how many are shown AND the true total");
  is(text(dom).indexOf("39"), -1,
     "and no combined total appears anywhere on the screen");

  /* Both headings, for somebody who is both. */
  dom = await load("#team", makeFrame({ is_hr: true }), makeCounts(), {
    [TEAM]: Object.assign(makeTeam(), {
      direct: { rows: [row("HR-EMP-2", "Anita Sharma", BOTH_ACTIONS,
                           { also_covered: true })],
                total: 1, capped: false, cap: 50 },
      covered: { rows: [row("HR-EMP-9", "Deepak Rana", COVERED_ACTIONS,
                            { basis: "covered", also_covered: true })],
                 total: 1, capped: false, cap: 50 },
      is_hr_scope: true, has_direct: true, has_covered: true }),
  });
  is(headings(dom).filter((h) => h.indexOf("Your team") === 0 ||
                                 h.indexOf("You cover") === 0).length, 2,
     "somebody who is both sees both headings");
  is((text(dom).match(/Anita Sharma/g) || []).length, 1,
     "AC-75: the both-person appears exactly once, under Your team");

  /* ── Team: the screen offers exactly what the server allows ──────────── */

  /* The both-person's sheet: the manager actions AND the HR-only ones. */
  let btns = screens(dom).querySelectorAll("[data-person]");
  btns[0].dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(sheetOpen(dom), true, "tapping a person opens the sheet");
  is(/Approve as HR/.test(sheetText(dom)), true,
     "AC-82: the HR override reads 'Approve as HR', never plain 'Approve'");
  is(/Cancel an attendance deduction/.test(sheetText(dom)), true,
     "AC-75: and the HR-only actions are on the both-person's row");
  is(/Approve or decline leave/.test(sheetText(dom)), true,
     "with the manager actions still there");

  /* A covered row: NO manager action, anywhere in the markup. */
  dom.window.NextFrame.closeSheet();
  btns = screens(dom).querySelectorAll("[data-person]");
  btns[1].dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(/Approve or decline leave/.test(sheetText(dom)), false,
     "AC-77: a covered row offers no leave approval - absent, not disabled");
  is(/Set or change goals/.test(sheetText(dom)), false,
     "and no set-goals control");
  is(sheetText(dom).indexOf("Approve as HR") >= 0, true,
     "what it does offer is the HR act, named as one");
  is(el(dom, "nf-sheet-body").querySelectorAll("button[disabled]").length, 0,
     "nothing is offered as a greyed-out control (01b rule 1)");

  /* **The screen never invents an action the server did not send.** */
  dom = await load("#team", makeFrame(), makeCounts(), {
    [TEAM]: Object.assign(makeTeam(), {
      direct: { rows: [row("HR-EMP-2", "Anita Sharma", ["open_record"])],
                total: 1, capped: false, cap: 50 } }),
  });
  screens(dom).querySelector("[data-person]")
    .dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(/Approve/.test(sheetText(dom)), false,
     "a row the server gave one action gets one action, and no more");
  is(/Open their record/.test(sheetText(dom)), true, "and it gets that one");

  /* Escape closes the sheet and gives focus back - the frame's behaviour,
     used rather than copied. */
  const opener = screens(dom).querySelector("[data-person]");
  dom.window.document.dispatchEvent(
    new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await settle();
  is(sheetOpen(dom), false, "Escape closes the person sheet");
  is(dom.window.document.activeElement === opener, true,
     "and focus goes back to the row that opened it");

  /* An empty scope is a sentence, never a blank screen (AC-49). */
  dom = await load("#team", makeFrame({ is_hr: true, has_reports: false }),
                   makeCounts(), {
    [TEAM]: Object.assign(makeTeam(), {
      direct: { rows: [], total: 0, capped: false, cap: 50 },
      covered: { rows: [], total: 0, capped: false, cap: 50 },
      is_hr_scope: true, has_direct: false, has_covered: false }),
  });
  is(/Nobody is in your scope yet/.test(text(dom)), true,
     "AC-49: an empty scope gets the sentence, not a blank screen");

  /* A hostile designation. */
  dom = await load("#team", makeFrame(), makeCounts(), {
    [TEAM]: Object.assign(makeTeam(), {
      direct: { rows: [row("HR-EMP-2", "Anita Sharma", ["open_record"],
                           { designation: NASTY })],
                total: 1, capped: false, cap: 50 } }),
  });
  is(screens(dom).querySelectorAll("img[src='x']").length, 0,
     "AC-85: a hostile job title creates no element on Team");
  is(text(dom).indexOf(NASTY) >= 0, true, "it appears as text instead");
  is(dom.window.__alerted, false, "and nothing executed");

  /* ── Growth: the two figures never meet ─────────────────────────────── */

  dom = await load("#growth", makeFrame(), makeCounts(), { [GROWTH]: makeGrowth() });
  is(kind(dom), null, "Growth is not showing an error or a spinner");
  is(text(dom).indexOf("28.4") >= 0, true, "the approved figure is on the screen");
  is(/3\.1 Lakh is waiting for Sakshi Verma/.test(text(dom)), true,
     "AC-29: the waiting amount is named, with who it is waiting for");
  is(text(dom).indexOf("31.5"), -1,
     "and 31.5 appears NOWHERE - nothing on this screen adds the two");
  is(/does not move until it is approved/.test(text(dom)), true,
     "and the screen says why the figure has not moved");

  /* The chip: words, and a date when it is old. */
  is(/At Risk/.test(text(dom)), true, "the trajectory is in words, not only colour");
  is(/Not set yet/.test(text(dom)), true,
     "AC-67: a goal with no trajectory says 'Not set yet', never 'Off Track'");
  is(text(dom).indexOf("0 %"), -1, "and never 0 %");

  is(/Needs attention \(1\)/.test(text(dom)), true,
     "the needs-attention count is in its heading");
  is(screens(dom).querySelectorAll(".nf-rows .nf-row").length, 1,
     "and equals the number of rows under it");

  dom = await load("#growth", makeFrame(), makeCounts(), {
    [GROWTH]: Object.assign(makeGrowth(), {
      goals: [Object.assign({}, makeGrowth().goals[0], {
        trajectory: { state: "On Track", as_of: "2026-09-10", stale: true,
                      needs_attention: false } })],
      needs_attention: [] }),
  });
  is(/On Track, as of 2026-09-10/.test(text(dom)), true,
     "AC-24: a stale chip carries the date it was worked out");

  /* No cycle, and no goals. */
  dom = await load("#growth", makeFrame(), makeCounts(), {
    [GROWTH]: Object.assign(makeGrowth(), { cycle: null, goals: [],
                                            needs_attention: [] }),
  });
  is(/There is no review running right now/.test(text(dom)), true,
     "AC-43: no cycle is a sentence, never an empty wizard");
  is(/No goals have been set for you yet/.test(text(dom)), true,
     "AC-44: and no goals is its own sentence");

  /* No manager recorded. */
  dom = await load("#growth", makeFrame(), makeCounts(), {
    [GROWTH]: Object.assign(makeGrowth(), {
      review: { appraisal: "", status: "", goes_to: "", has_manager: false,
                can_open: false } }),
  });
  is(/Nobody is recorded as your manager/.test(text(dom)), true,
     "AC-59: an employee with no manager is told on the screen");

  /* ── the self-review wizard ─────────────────────────────────────────── */

  dom = await load("#growth/review", makeFrame(), makeCounts(),
                   { [REVIEW]: makeReview() });
  is(kind(dom), null, "the wizard drew");
  is(/Step 0 of 5/.test(text(dom)), true,
     "AC-28: with nothing answered it says step 0, not step 1 for being open");

  /* Whole points: five buttons, and no control that can produce a half. */
  let rateBtns = screens(dom).querySelectorAll("[data-rate]");
  is(rateBtns.length, 5, "the rating is five whole-point buttons");
  is(screens(dom).querySelectorAll('input[type="range"]').length, 0,
     "and there is no slider anywhere - a slider can be un-snapped");
  is(Array.from(rateBtns).map((b) => b.getAttribute("data-rate")).join(","),
     "1,2,3,4,5", "each button is a whole number");

  rateBtns[2].dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(screens(dom).querySelector(".nf-rate-on").getAttribute("aria-pressed"), "true",
     "the chosen rating says so in its accessible name, not only in its colour");

  /* Every company value, read from the tenant. SEVEN. */
  dom = await load("#growth/review", makeFrame(), makeCounts(),
                   { [REVIEW]: makeReview() });
  dom.window.NextGrowth._state().step = 0;
  el(dom, "nf-wiz-next").dispatchEvent(
    new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(/Value 1 of 7/.test(text(dom)), true, "the values step numbers each value");
  is(/Value 7 of 7/.test(text(dom)), true,
     "and offers all SEVEN - nothing counts five");
  is(screens(dom).querySelectorAll(".nf-rate").length, 7,
     "every one of them has its own rating control");

  /* A tenant with three gets three. */
  const three = makeReview();
  three.values = three.values.slice(0, 3);
  three.values_count = 3;
  dom = await load("#growth/review", makeFrame(), makeCounts(), { [REVIEW]: three });
  el(dom, "nf-wiz-next").dispatchEvent(
    new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(screens(dom).querySelectorAll(".nf-rate").length, 3,
     "a tenant with three values gets three, not five and not seven");

  /* A hostile company value name. */
  const nastyValues = makeReview();
  nastyValues.values[0].value_name = NASTY;
  dom = await load("#growth/review", makeFrame(), makeCounts(),
                   { [REVIEW]: nastyValues });
  el(dom, "nf-wiz-next").dispatchEvent(
    new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(screens(dom).querySelectorAll("img[src='x']").length, 0,
     "AC-85: a hostile company value name creates no element");
  is(dom.window.__alerted, false, "and nothing executed");

  /* ── the byte budget, watched while somebody types ──────────────────── */

  dom = await load("#growth/review", makeFrame(), makeCounts(),
                   { [REVIEW]: makeReview() });
  is(/characters left/.test(el(dom, "nf-wiz-room").textContent), true,
     "the room left is on the screen before anything is typed");

  const G = dom.window.NextGrowth;
  is(G.bytesOf("abc"), 3, "an English character costs one byte");
  is(G.bytesOf("ककक"), 9,
     "a Devanagari character costs three - which is the whole point of a " +
     "budget in bytes");

  /* Type past the ceiling and the screen says so, in the characters being
     typed, BEFORE anything is sent. */
  const body = screens(dom).querySelector("textarea[data-id]") ||
               screens(dom).querySelector("textarea");
  body.value = "क".repeat(30000);
  body.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  await settle();
  const room = el(dom, "nf-wiz-room");
  is(room.getAttribute("data-over"), "yes",
     "past the ceiling the room line flips to over");
  is(/too long/.test(room.textContent), true, "and says so in words");
  is(/characters/.test(room.textContent), true,
     "counted in characters, not in bytes a person cannot see");
  is(dom.window.calls.filter((c) => c === SAVE).length, 0,
     "and NOTHING was sent - the autosave does not fail silently while " +
     "somebody keeps typing");

  /* An unchanged step sends nothing at all. */
  dom = await load("#growth/review", makeFrame(), makeCounts(),
                   { [REVIEW]: makeReview(), [SAVE]: { saved_at: "2026-09-24 10:00:00",
                     used_bytes: 20, budget_bytes: 63487,
                     room_left_characters: 63000 } });
  el(dom, "nf-wiz-next").dispatchEvent(
    new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  is(dom.window.calls.filter((c) => c === SAVE).length, 0,
     "AC-37: a step nobody changed sends nothing");

  /* A change, then a step change, saves once - and the time shown is the
     SERVER's. */
  const text2 = screens(dom).querySelector("textarea");
  text2.value = "Something I typed.";
  text2.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  await settle();
  el(dom, "nf-wiz-next") &&
    el(dom, "nf-wiz-next").dispatchEvent(
      new dom.window.MouseEvent("click", { bubbles: true }));
  await settle();
  await settle();
  is(dom.window.calls.filter((c) => c === SAVE).length, 1,
     "a changed step saves once on the way out");
  is(/Saved at 10:00/.test(el(dom, "nf-wiz-room").textContent), true,
     "AC-37: and the time shown is the server's confirmed time, not the " +
     "browser's clock");

  /* A refusal is the server's sentence, not a page error. */
  dom = await load("#growth", makeFrame(), makeCounts(),
                   { [GROWTH]: { refuse: "This page is not part of your access." } });
  is(kind(dom), null, "a refused Growth call is not a page error");
  is(/not part of your access/.test(text(dom)), true,
     "it is the server's own sentence");

  console.log("\nnext growth and team: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

run();
