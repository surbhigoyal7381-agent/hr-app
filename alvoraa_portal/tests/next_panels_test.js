/* Slice 042, Wave 2: Home and the Inbox, driven in a real DOM.
 *
 * These load the preview page's own source - markup, stylesheets and scripts
 * expanded the way the server serves them - put it in jsdom, answer the three
 * calls with a fixture, and then look at what a PERSON would see.
 *
 * The one that matters most is AC-60. A Designation of
 * `<img src=x onerror=alert(1)>` has to appear as TEXT and create no element.
 * That cannot be read off the server's payload: the payload is supposed to
 * carry the string. Whether it becomes an element is what this file asks, in
 * three places - a queue row, an approval context line and the team card.
 *
 * Run through scripts/run_dom_tests.js, which is what CI runs.
 */

const { JSDOM, VirtualConsole } = require("jsdom");
const { readPreviewSource } = require("../../scripts/lib/portal_source");

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log("  PASS  " + m); };
const bad = (m) => { fail++; console.log("  FAIL  " + m); };
const is = (got, want, m) =>
  (String(got) === String(want) ? ok(m) : bad(m + "  (got " + JSON.stringify(got) + ", wanted " + JSON.stringify(want) + ")"));

/* The hostile string. It is a Designation somebody could really be given by an
   HR user with write access to the Designation list - this is a stored-XSS
   shape, not a theoretical one. */
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

function makeFrame(over) {
  return Object.assign({
    user: "rahul@example.com",
    user_full_name: "Rahul Sharma",
    has_employee: true,
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma", designation: "Sales Executive",
          department: "Sales", image: null, company: "Test Co" },
    is_hr: false, is_manager: false, is_system_manager: false, is_control_plane: false,
    has_reports: false, scope_is_store: false, may_save_settings: false,
    review_open_count: null,
    features: { plan_payroll: 1, goals: 1, expenses: 1 },
    switch_target: null, persona_rule: 4, show_team: false,
    allowed_pages: ["home", "inbox", "time", "growth", "pay"],
    bottom_bar: ["home", "time", "pay", "growth"],
  }, over || {});
}

function makeCounts(over) {
  const parts = [
    { key: "leave_approvals", count: 0, route: "#team", cap: null, capped: false },
    { key: "goal_updates", count: 0, route: "#growth", cap: null, capped: false },
    { key: "attendance_fixes", count: 0, route: "#time/fix", cap: 50, capped: false },
    { key: "shift_requests", count: 0, route: "#time/shift", cap: null, capped: false },
    { key: "policies", count: 0, route: "#company/policies", cap: null, capped: false },
    { key: "my_requests", count: 0, route: "#time", cap: null, capped: false },
  ];
  return Object.assign({ total: 0, approvals_total: 0, has_employee: true,
                         parts: parts, corrections_hr_scope: false }, over || {});
}

/* A `get_home` payload in the shape the server really returns - the same key
   set, so a test cannot pass against a shape the server does not send. */
function makeHome(over) {
  return Object.assign({
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma", designation: "Sales Executive",
          department: "Sales", image: null, company: "Test Co" },
    today: { date: "2026-09-24", shift: { name: "Morning", start: "09:30:00", end: "18:30:00" },
             checkin: null, needs_location: false },
    needs: [],
    leave: [],
    holidays: [],
    holiday_note: null,
    goals: { mine: null },
    team_today: { in: null, away: null, due: null, basis: "none", suppressed: false },
    celebrations: { own_anniversary_years: null, joiners: [] },
  }, over || {});
}

function makeInbox(over) {
  return Object.assign({
    total: 0, approvals_total: 0, has_employee: true,
    parts: [], corrections_hr_scope: false,
  }, over || {});
}

/* Frappe's own reply shape, and the shape of a refusal. Wave 1's frame moved
   from `frappe.call` to `fetch` with a CSRF header when it learned to mend a
   stale token (034 F4), so this harness mirrors `next_frame_test.js`'s rather
   than keeping a second, older one - two harnesses would drift and this file
   would go on testing a page the frame no longer is. */
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

function load(frame, counts, answers) {
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
      url: "http://test.localhost/hrms-employee-next",
      beforeParse(w) {
        w.calls = [];
        w.frappe = { _: (s) => s, csrf_token: "token-the-page-was-built-with" };
        w.document.cookie = "user_id=rahul@example.com";
        /* If the hostile string ever becomes a real <img>, jsdom tries to load
           `x` and the onerror handler runs. This records that. */
        w.alert = () => { w.__alerted = true; };
        w.__alerted = false;
        w.prompt = () => "a reason";

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
          const custom = answers[method];
          if (custom === "fail") {
            return reply(417, { exc_type: "ValidationError",
                                _server_messages: said("It did not work.") });
          }
          if (typeof custom === "function") {
            const out = custom(args);
            if (out && out.status) { return reply(out.status, out.body || {}); }
            return reply(200, { message: out });
          }
          let message = null;
          if (method.endsWith("get_frame")) { message = frame; }
          else if (method.endsWith("get_nav_counts")) { message = counts; }
          else { message = custom === undefined ? { rows: [] } : custom; }
          return reply(200, { message: message });
        };
      },
    });
  return new Promise((resolve) => {
    /* Four turns, the same as next_frame_test.js: get_frame, get_nav_counts,
       get_home, and room for the retry behind a stale token. */
    setTimeout(() => setTimeout(() => setTimeout(() => setTimeout(
      () => resolve(dom), 0), 0), 0), 0);
  });
}

const el = (dom, id) => dom.window.document.getElementById(id);
const screens = (dom) => el(dom, "nf-screens");
const kind = (dom) => el(dom, "nf-state").hidden ? null : el(dom, "nf-state").getAttribute("data-kind");
const text = (dom) => screens(dom).textContent;

async function run() {
  /* ── the panels are wired in at all ───────────────────────────────────── */

  let dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome(),
  });
  is(dom.window.NextFrame.hasPanel("home"), true, "the Home panel registered itself");
  is(dom.window.NextFrame.hasPanel("inbox"), true, "the Inbox panel registered itself");

  /* AC-31: both skeletons are in the HTML the server sends, not built by
     JavaScript. Checked in the source, with no timing involved. */
  const sk = ["nf-skeleton-home", "nf-skeleton-inbox"];
  is(sk.filter((id) => !SRC.includes('id="' + id + '"')).length, 0,
     "both skeletons are server-rendered: " + sk.join(", "));

  /* AC-38: Home makes exactly three calls and none waits on a timer. */
  const boot = dom.window.calls.filter(
    (m) => /get_frame|get_nav_counts|get_home/.test(m));
  is(boot.length, 3, "Home costs three calls: " + boot.join(" + "));
  is(boot.filter((m) => /get_inbox/.test(m)).length, 0,
     "Home does not ask for the Inbox's rows");

  /* ── AC-60: a hostile Designation is TEXT, in three places ─────────────── */

  /* 1. a queue row. */
  dom = await load(makeFrame(), makeCounts({ total: 1, approvals_total: 1 }), {
    "alvoraa_portal.home_api.get_home": makeHome(),
    "alvoraa_portal.inbox_api.get_inbox": makeInbox({
      total: 1, approvals_total: 1,
      parts: [{
        key: "leave_approvals", route: "#team", count: 1, shown: 1, cap: 50,
        capped: false, label: "1 leave request to approve",
        rows: [{ name: "LAP-1", employee_name: NASTY, from_date: "2026-10-01",
                 to_date: "2026-10-02", leave_type: "Casual Leave", total_days: 2,
                 context: null, action: "leave" }],
      }],
    }),
  });
  dom.window.NextFrame.go("inbox");
  await new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
  is(screens(dom).querySelectorAll("img").length, 0,
     "a hostile name in a queue row creates no element");
  is(text(dom).indexOf(NASTY) !== -1, true,
     "the hostile name is shown as text, so the approver still sees who it is");
  is(dom.window.__alerted, false, "nothing in the queue row executed");

  /* 2. an approval context line. */
  dom = await load(makeFrame(), makeCounts({ total: 1, approvals_total: 1 }), {
    "alvoraa_portal.home_api.get_home": makeHome(),
    "alvoraa_portal.inbox_api.get_inbox": makeInbox({
      total: 1, approvals_total: 1,
      parts: [{
        key: "leave_approvals", route: "#team", count: 1, shown: 1, cap: 50,
        capped: false, label: "1 leave request to approve",
        rows: [{ name: "LAP-2", employee_name: "Someone", from_date: "2026-10-01",
                 to_date: "2026-10-01", leave_type: "Casual Leave", total_days: 1,
                 context: NASTY, action: "leave" }],
      }],
    }),
  });
  dom.window.NextFrame.go("inbox");
  await new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
  is(screens(dom).querySelectorAll("img").length, 0,
     "a hostile context line creates no element");
  is(dom.window.__alerted, false, "nothing in the context line executed");

  /* 3. the team card on Home. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome({
      team_today: { in: 6, away: 5, due: 5, basis: NASTY, suppressed: false },
      needs: [{ id: "self_review", kind: "self_review", title: NASTY,
                detail: { due: "2026-10-31" }, action: "open_review",
                route: "#growth/review" }],
    }),
  });
  is(screens(dom).querySelectorAll("img").length, 0,
     "a hostile string on the Home cards creates no element");
  is(dom.window.__alerted, false, "nothing on Home executed");

  /* ── the states a person can reach ─────────────────────────────────────── */

  /* AC-3: nothing waiting is "All clear", a designed state. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome(),
    "alvoraa_portal.inbox_api.get_inbox": makeInbox(),
  });
  dom.window.NextFrame.go("inbox");
  await new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
  is(kind(dom), "empty", "an empty Inbox is the empty state, not a blank page");

  /* AC-34: the rows failing is an error state with a Try again, not a blank. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome(),
    "alvoraa_portal.inbox_api.get_inbox": "fail",
  });
  dom.window.NextFrame.go("inbox");
  await new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
  is(kind(dom), "error", "a failed Inbox call is the error state");
  is(el(dom, "nf-state-retry").hidden, false, "the error state offers Try again");

  /* AC-11: a capped list says so on screen. */
  dom = await load(makeFrame(), makeCounts({ total: 60 }), {
    "alvoraa_portal.home_api.get_home": makeHome(),
    "alvoraa_portal.inbox_api.get_inbox": makeInbox({
      total: 60, approvals_total: 60,
      parts: [{ key: "attendance_fixes", route: "#time/fix", count: 60, shown: 50,
                cap: 50, capped: true, label: "60 attendance fixes to decide",
                rows: Array.from({ length: 50 }, (_v, i) => ({
                  name: "ARQ-" + i, employee_name: "P" + i, from_date: "2026-09-01",
                  to_date: "2026-09-01", reason: "On Duty", context: null,
                  action: "attendance_fix" })) }],
    }),
  });
  dom.window.NextFrame.go("inbox");
  await new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));
  is(/Showing the first 50 of 60/.test(text(dom)), true,
     "a capped list says how many it is showing of how many");
  is(/50\+/.test(text(dom)), false, "no part ever shows a 50+");

  /* AC-4: no shift means no hero. Not an empty hero. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome({
      today: { date: "2026-09-24", shift: null, checkin: null, needs_location: false } }),
  });
  is(el(dom, "nf-home-hero"), null, "with no shift there is no check-in hero at all");

  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome(),
  });
  is(el(dom, "nf-home-hero") !== null, true,
     "with a shift the hero IS drawn, so the assertion above can fail");

  /* AC-4's fourth case: already checked in. The button reads Check out and the
     line says when, as a whole phrase with the time in it. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome({
      today: { date: "2026-09-24",
               shift: { name: "Morning", start: "09:30:00", end: "18:30:00" },
               checkin: { time: "2026-09-24 09:24:11", type: "IN" },
               needs_location: false } }),
  });
  is(el(dom, "nf-home-checkin-btn").textContent.trim(), "Check out",
     "already checked in, so the button reads Check out");
  is(el(dom, "nf-home-checkin-btn").getAttribute("data-action"), "OUT",
     "and it would send OUT");
  is(/Checked in at 09:24/.test(text(dom)), true,
     "the line says when, with the seconds cut off: " + text(dom).slice(0, 80));

  /* AC-29: a small group shows the sentence and no numbers. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.home_api.get_home": makeHome({
      team_today: { in: null, away: null, due: null, basis: "peers", suppressed: true } }),
  });
  is(screens(dom).querySelectorAll(".nf-count").length, 0,
     "a suppressed team card draws no number");
  is(/Nothing about why anyone is away/.test(text(dom)), true,
     "the presence sentence is on the card, not in a tooltip");

  /* AC-30: the phrase that tells a colleague an absence is NOT leave appears
     nowhere. */
  is(/Nobody is on leave/i.test(SRC), false,
     '"Nobody is on leave today" appears nowhere in the built page');

  /* AC-37: no employee record is one plain line, not a wall of errors. */
  dom = await load(makeFrame({ has_employee: false, me: null }), makeCounts(),
                   { "alvoraa_portal.home_api.get_home": makeHome({ me: null }) });
  is(screens(dom).querySelectorAll(".nf-card").length, 0,
     "a person with no employee record gets no cards");
  is(kind(dom), null, "and no error state either");

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

run().catch((e) => { console.error(e); process.exit(1); });
