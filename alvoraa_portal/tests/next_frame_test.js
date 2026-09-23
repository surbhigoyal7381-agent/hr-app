/* Slice 034, Wave 1: the frame, driven in a real DOM.
 *
 * These load the preview page's own source - markup, stylesheet and script
 * expanded into one document, the way the server serves it - put it in jsdom,
 * answer its two start-up calls with a fixture, and then click it.
 *
 * Why in a browser and not in Python: every one of these is a statement about
 * what a PERSON sees. "The bell shows no number when nothing is waiting" and
 * "the menu holds no entry this person cannot use" cannot be read off the
 * server's payload - they are what the page does with it, and that is where the
 * mistakes live.
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

/* The page is a Jinja template. jsdom is not Jinja, so the handful of tags in
   it are filled with fixture values first. Only the frame's own tags appear
   here; if a new one is added and this list is not, the assertion below about
   leftover tags fails rather than the page quietly rendering "{{ something }}"
   as text on screen. */
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

/* A frame payload in the shape `frame_api.get_frame` really returns. Written
   once so that every test below starts from a real persona rather than from
   whatever that test happened to need. */
function makeFrame(over) {
  return Object.assign({
    user: "rahul@example.com",
    user_full_name: "Rahul Sharma",
    has_employee: true,
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma", designation: "Sales Executive",
          department: "Sales", image: null, company: "Test Co" },
    is_hr: false,
    is_manager: false,
    is_system_manager: false,
    is_control_plane: false,
    has_reports: false,
    scope_is_store: false,
    may_save_settings: false,
    review_open_count: null,
    features: { plan_payroll: 1, goals: 1, expenses: 1 },
    switch_target: null,
    persona_rule: 4,
    show_team: false,
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
  const base = { total: 0, approvals_total: 0, has_employee: true, parts: parts,
                 corrections_hr_scope: false };
  return Object.assign(base, over || {});
}

const SRC = fillTemplate(readPreviewSource());

/* The stub is `fetch`, not `frappe.call`, because `fetch` is what the frame
   really uses.

   It used to stub `frappe.call`, and that stub was MORE capable than the real
   thing: it called `opts.error` on a failure. Website pages load website.js's
   `frappe.call`, which never calls `opts.error` at all - so every error test in
   this file was passing against behaviour no browser has. Proved in a real
   browser on 2026-09-24. A stub may be simpler than the real thing; it may not
   be kinder. */
function reply(status, payload) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status: status,
    statusText: String(status),
    text: () => Promise.resolve(JSON.stringify(payload)),
  });
}

/* Frappe's shape for a refusal: the sentence arrives inside _server_messages. */
function said(sentence) {
  return JSON.stringify([JSON.stringify({ message: sentence })]);
}

/* One page, one fixture, one promise that resolves when the frame has finished
   booting. `answers` lets a test make a call fail, which is the only way to
   reach the error states. An answer may be:
     "fail"        - 417, the way a server error arrives
     "expired"     - 403 AND the user_id cookie rewritten to Guest, which is
                     exactly what Frappe does when a session has ended
     "refused"     - 403 with the person still signed in
     "stale-once"  - 400 CSRFTokenError first, then the real answer
     a function    - (args, attempt) => message, or {status, body}
*/
function load(frame, counts, answers) {
  answers = answers || {};
  /* jsdom cannot follow a link, so it reports one instead. That report is how
     we prove the signed-out redirect happened without a browser: the frame
     setting window.location.href is the only thing here that tries to leave
     the page. */
  const navTried = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => {
    if (/Not implemented: navigation/.test(e.message)) { navTried.push(e.message); }
    else { console.error(e.message); }
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
        w.sent = [];          /* {method, token} for every POST that went out */
        w.pageReads = 0;      /* how many times the token was re-read */
        w.frappe = { _: (s) => s, csrf_token: "token-the-page-was-built-with" };
        w.document.cookie = "user_id=rahul@example.com";
        const attempts = {};

        w.fetch = (url, opts) => {
          url = String(url);
          /* The frame re-reads its own page to mend a stale token. */
          if (url.indexOf("/api/method/") !== 0) {
            w.pageReads += 1;
            return Promise.resolve({
              ok: true, status: 200, statusText: "OK",
              text: () => Promise.resolve(
                '<script>frappe.csrf_token = "a-fresh-token"</script>'),
            });
          }

          const method = url.slice("/api/method/".length);
          const token = opts && opts.headers && opts.headers["X-Frappe-CSRF-Token"];
          w.calls.push(method);
          w.sent.push({ method: method, token: token });
          attempts[method] = (attempts[method] || 0) + 1;
          const args = opts && opts.body ? JSON.parse(opts.body) : {};
          const custom = answers[method];

          if (custom === "fail") {
            return reply(417, { exc_type: "ValidationError",
                                _server_messages: said("It did not work.") });
          }
          if (custom === "expired") {
            /* Frappe turns the caller into Guest and says so in the cookie. */
            w.document.cookie = "user_id=Guest";
            return reply(403, { exc_type: "PermissionError",
                                _server_messages: said("Not permitted") });
          }
          if (custom === "refused") {
            return reply(403, { exc_type: "PermissionError",
                                _server_messages: said("Not permitted") });
          }
          if (custom === "stale-once" && attempts[method] === 1) {
            return reply(400, { exc_type: "CSRFTokenError", message: "Invalid Request" });
          }
          if (typeof custom === "function") {
            const out = custom(args, attempts[method]);
            if (out && out.status) { return reply(out.status, out.body || {}); }
            return reply(200, { message: out });
          }

          let message = null;
          if (method.endsWith("get_frame")) { message = frame; }
          else if (method.endsWith("get_nav_counts")) { message = counts; }
          else if (custom === undefined || custom === "stale-once") { message = { rows: [] }; }
          else { message = custom; }
          return reply(200, { message: message });
        };
      },
    });
  return new Promise((resolve) => {
    /* A few turns of the loop: get_frame, get_nav_counts, and - where a token
       was stale - the page re-read and the one retry behind it. */
    setTimeout(() => setTimeout(() => setTimeout(() => setTimeout(
      () => { dom.navTried = navTried; resolve(dom); }, 0), 0), 0), 0);
  });
}

const el = (dom, id) => dom.window.document.getElementById(id);
const kind = (dom) => el(dom, "nf-state").hidden ? null : el(dom, "nf-state").getAttribute("data-kind");
const say = (dom) => el(dom, "nf-state-say").textContent;
const menuRoutes = (dom) =>
  Array.from(dom.window.document.querySelectorAll("#nf-menu [data-route]"))
    .map((n) => n.getAttribute("data-route"));
const tabs = (dom) =>
  Array.from(dom.window.document.querySelectorAll("#nf-bottom .nf-tab"))
    .map((n) => n.textContent.trim());

async function run() {
  /* ── the page the server sends ─────────────────────────────────────────── */

  if (/\{\{|\{%/.test(SRC)) {
    bad("the preview page still holds Jinja tags this test does not fill - it would render them as text");
  } else {
    ok("every Jinja tag in the preview page is accounted for");
  }

  /* AC-31: the shell and the skeleton are in the HTML the server sends, not
     built by JavaScript. Checked in the source, with no timing involved. */
  const skeleton = ["nf-rail", "nf-top", "nf-main", "nf-bottom", "nf-sheet", "nf-toasts"];
  const missing = skeleton.filter((id) => !SRC.includes('id="' + id + '"'));
  is(missing.length, 0, "the shell is server-rendered: " + skeleton.join(", "));

  /* ── the menu (US-1) ───────────────────────────────────────────────────── */

  let dom = await load(makeFrame(), makeCounts());
  const rahul = menuRoutes(dom);
  is(rahul.indexOf("team"), -1, "an employee gets no Team entry");
  is(rahul.indexOf("company/settings"), -1, "an employee gets no Org settings entry");
  is(rahul.indexOf("home") !== -1 && rahul.indexOf("pay/expenses") !== -1, true,
     "an employee's menu holds Home and Expenses: " + rahul.join(", "));

  /* AC-6: nothing is greyed out. An entry a person cannot use is not drawn. */
  const disabled = dom.window.document.querySelectorAll(
    "#nf-menu [disabled], #nf-menu [aria-disabled='true'], #nf-bottom [disabled], #nf-top [disabled]");
  is(disabled.length, 0, "no entry in the rail, top bar or bottom bar is disabled");

  /* AC-7: exactly two start-up calls, and neither waits on a timer. */
  const boot = dom.window.calls.filter((m) => /get_frame|get_nav_counts/.test(m));
  is(boot.length, 2, "boot makes exactly two calls: " + boot.join(" + "));

  /* AC-1 / AC-44: no payroll means no My pay entry, and Expenses is still
     reachable. */
  dom = await load(makeFrame({ features: { goals: 1, expenses: 1 } }), makeCounts());
  const noPay = menuRoutes(dom);
  is(noPay.indexOf("pay"), -1, "without payroll there is no My pay entry");
  is(noPay.indexOf("pay/expenses") !== -1, true, "without payroll Expenses is still there (AC-1)");
  is(dom.window.NextFrame.defaultRouteFor("pay"), "pay/expenses",
     "the Pay button opens Expenses on a tenant without payroll");

  /* Typing #pay on that tenant shows the no-permission sentence, not an empty
     salary tab (AC-44). */
  dom.window.location.hash = "#pay";
  dom.window.NextFrame.route();
  is(kind(dom), "refused", "typing #pay without payroll shows the refusal state");
  is(say(dom), dom.window.NextFrame.SAY.noPermission, "and it is section 6's sentence");

  /* AC-45: an absent staff-list key HIDES the staff list, and an absent
     org-structure key SHOWS the org chart. The two are independent. */
  const hrBase = { is_hr: true, has_reports: false, persona_rule: 2, show_team: true,
                   allowed_pages: ["home", "inbox", "time", "growth", "pay", "team", "company"],
                   bottom_bar: ["home", "inbox", "company", "team"] };
  dom = await load(makeFrame(Object.assign({}, hrBase, { features: { goals: 1 } })), makeCounts());
  is(menuRoutes(dom).indexOf("company/staff"), -1,
     "an absent staff-list key hides the staff list - an opt-in feature must not appear because a read failed");
  is(menuRoutes(dom).indexOf("company/people") !== -1, true,
     "an absent plan_org_structure still shows the org chart");

  dom = await load(makeFrame(Object.assign({}, hrBase, {
    features: { goals: 1, plan_staff_list: true, plan_org_structure: false } })), makeCounts());
  const split = menuRoutes(dom);
  is(split.indexOf("company/staff") !== -1, true,
     "with the switch on and the org chart off, the staff list is there");
  is(split.indexOf("company/people"), -1,
     "and the org chart entry is not - the two flags are independent (W1D-21)");

  /* The staff list entry is hidden for a non-HR caller even where the tenant
     has the feature: it is an HR screen and the endpoint refuses them. */
  dom = await load(makeFrame({ features: { plan_payroll: 1, plan_staff_list: true } }), makeCounts());
  is(menuRoutes(dom).indexOf("company/staff"), -1,
     "a plain employee gets no staff-list entry even when the tenant has the switch on");

  /* ── the bottom bar (US-3) ─────────────────────────────────────────────── */

  dom = await load(makeFrame(Object.assign({}, hrBase, { features: { goals: 1 } })), makeCounts());
  const hrTabs = tabs(dom);
  is(hrTabs.slice(0, 4).join(" · "), "Home · Inbox · Company · Team",
     "an HR user with no reports gets Home, Inbox, Company, Team (W1D-20)");
  is(hrTabs[hrTabs.length - 1], "More", "More is always last");

  /* Asha: no Employee record. Three buttons, and no Time button anywhere -
     AC-10 and AC-63 have to agree. */
  dom = await load(makeFrame({
    has_employee: false, me: null, is_hr: true, is_system_manager: true,
    persona_rule: 6, allowed_pages: ["home", "inbox", "company"],
    bottom_bar: ["home", "inbox", "company"], features: {},
  }), makeCounts({ has_employee: true }));
  is(tabs(dom).join(" · "), "Home · Inbox · Company",
     "a person with no employee record gets three buttons and no More");
  is(menuRoutes(dom).indexOf("time"), -1, "and no Time entry at all (AC-63)");
  dom.window.location.hash = "#home";
  dom.window.NextFrame.route();
  is(el(dom, "nf-screens").textContent.includes("not linked to an employee record"), true,
     "their Home says so plainly");
  is(kind(dom), null, "and it is a screen, not an error state (AC-63)");

  /* ── routes, titles and focus (US-4) ───────────────────────────────────── */

  dom = await load(makeFrame(), makeCounts());
  dom.window.location.hash = "#nonsense";
  dom.window.NextFrame.route();
  is(dom.window.location.hash, "#home", "an unknown address opens Home");
  is(kind(dom), null, "and leaves no error behind (AC-14)");

  dom.window.NextFrame.go("time/days");
  is(el(dom, "nf-page").textContent, "My days", "the title is the page, in words");
  is(el(dom, "nf-group").textContent, "Time", "with the group above it");
  is(dom.window.document.activeElement.id, "nf-page",
     "focus moves to the page heading after a page change (AC-15)");
  const currentItems = dom.window.document.querySelectorAll("#nf-menu [aria-current='page']");
  is(currentItems.length, 1, "exactly one menu entry is marked as the current page");

  /* ── the bell and the count (US-6) ─────────────────────────────────────── */

  is(el(dom, "nf-bell-badge").hidden, true, "a badge of zero shows no number (AC-61)");
  is(el(dom, "nf-bell-label").textContent, "Inbox, nothing waiting",
     "and a screen reader hears that nothing is waiting");

  const parts = makeCounts().parts.map((p) =>
    p.key === "leave_approvals" ? Object.assign({}, p, { count: 3 }) : p);
  dom = await load(makeFrame(Object.assign({}, hrBase, { features: { goals: 1 } })),
                   makeCounts({ total: 3, approvals_total: 3, parts: parts }));
  is(el(dom, "nf-bell-badge").textContent, "3", "the bell shows the total");
  const inboxItem = dom.window.document.querySelector("#nf-menu [data-route='inbox'] .nf-count");
  is(inboxItem && inboxItem.textContent, "3", "the Inbox menu entry shows the same number");
  const inboxTab = Array.prototype.find.call(
    dom.window.document.querySelectorAll("#nf-bottom .nf-tab"),
    (n) => n.getAttribute("data-page") === "inbox");
  is(inboxTab.querySelector(".nf-badge").textContent, "3",
     "and so does the Inbox button on the bottom bar (AC-20)");

  dom.window.NextFrame.go("inbox");
  is(el(dom, "nf-screens").textContent.includes("3 leave requests to approve"), true,
     "the Inbox lists the one part that has something");
  is(el(dom, "nf-screens").textContent.includes("goal or KPI"), false,
     "a part with nothing in it is not shown (AC-23)");

  /* Where the screen behind a row is capped and the count is above the cap,
     the row says so rather than letting 50 stand for 60 (N3). */
  const capped = makeCounts().parts.map((p) =>
    p.key === "attendance_fixes" ? Object.assign({}, p, { count: 60, capped: true }) : p);
  dom = await load(makeFrame(Object.assign({}, hrBase, { features: { goals: 1 } })),
                   makeCounts({ total: 60, approvals_total: 60, parts: capped }));
  dom.window.NextFrame.go("inbox");
  is(el(dom, "nf-screens").textContent.includes("Showing the first 50 of 60"), true,
     "a capped row says how many the screen will show (N3)");

  dom = await load(makeFrame(), makeCounts());
  dom.window.NextFrame.go("inbox");
  is(kind(dom), "empty", "with nothing at all the Inbox is the empty state");
  is(say(dom), "All clear.", "and it reads 'All clear.'");

  /* ── the states (US-8) ─────────────────────────────────────────────────── */

  dom = await load(makeFrame(), makeCounts(), { "alvoraa_portal.inbox_api.get_nav_counts": "fail" });
  is(el(dom, "nf-bell-badge").hidden, true,
     "when the counts fail the bell shows no number (AC-32)");
  is(menuRoutes(dom).length > 0, true, "and the rest of the page still works");
  dom.window.NextFrame.go("inbox");
  is(kind(dom), "error", "the Inbox itself shows the card-error state");
  is(say(dom), "The waiting list could not load. Try again.", "in section 6's words");

  dom = await load(makeFrame(), makeCounts(), { "alvoraa_portal.frame_api.get_frame": "fail" });
  is(kind(dom), "error", "when get_frame fails the page shows the page-error state (AC-33)");
  is(el(dom, "nf-state-retry").hidden, false, "with a Try again button");
  const code = say(dom);
  is(/rahul|Sharma|example\.com/i.test(code), false,
     "and a code that holds no personal data");

  /* ---- a stale CSRF token (F4) -------------------------------------------

     The live portal has carried this cure since a desk page opening in another
     tab started breaking every open portal tab: the token a page was built
     with goes stale, the server answers 400, and the page mends itself once
     rather than telling a person the portal is broken. The frame had lost it.

     Without the retry this test fails on all three lines: the frame never
     boots, the page is never re-read, and nothing goes out a second time. */

  dom = await load(makeFrame(), makeCounts(),
                   { "alvoraa_portal.frame_api.get_frame": "stale-once" });
  is(kind(dom), null, "a stale token does not put the portal in the error state (F4)");
  is(menuRoutes(dom).length > 0, true, "the frame boots anyway, on a token read fresh");
  is(dom.window.pageReads, 1, "the page was re-read exactly once to mend the token");
  const frameSends = dom.window.sent.filter((s) => s.method.endsWith("get_frame"));
  is(frameSends.length, 2, "get_frame went out twice: the stale one and the retry");
  is(frameSends[1].token, "a-fresh-token", "and the retry carried the NEW token");

  /* One retry, not a loop. A server that keeps refusing must end as a refusal,
     or a broken session becomes a request every few milliseconds. */
  dom = await load(makeFrame(), makeCounts(), {
    "alvoraa_portal.frame_api.get_frame": () =>
      ({ status: 400, body: { exc_type: "CSRFTokenError", message: "Invalid Request" } }),
  });
  is(dom.window.sent.filter((s) => s.method.endsWith("get_frame")).length, 2,
     "a token that stays bad is tried twice and then given up on, not retried for ever");
  is(kind(dom), "error", "and the person gets the page-error state, not a spinner");

  /* ---- signed out, or simply refused (AC-62, F4) --------------------------

     Proved in a real browser on 2026-09-24: a session that has ended is
     answered 403 PermissionError, not 401, and the same response rewrites the
     user_id cookie to Guest. So 403 alone can mean either thing, and the
     cookie is what separates them. Treating every 403 as "signed out" bounces
     a signed-IN person between /login and this page for ever. */

  dom = await load(makeFrame(), makeCounts());
  const signedOut = dom.window.NextFrame.isSignedOut;
  is(signedOut({ status: 401 }), true, "401 is a session that has ended");
  is(signedOut({ exc_type: "AuthenticationError" }), true, "so is AuthenticationError");
  is(signedOut({ exc_type: "SessionExpired", status: 401 }), true, "so is SessionExpired");
  is(signedOut({ status: 417, exc_type: "ValidationError" }), false,
     "a server error is not a session that has ended");
  is(signedOut({ status: 403, exc_type: "PermissionError" }), false,
     "a 403 while still signed in is a refusal, not a sign-out - this is the bounce loop");

  dom = await load(makeFrame(), makeCounts(),
                   { "alvoraa_portal.frame_api.get_frame": "refused" });
  is(kind(dom), "error", "a refused signed-in caller sees the page-error state");
  is(dom.navTried.length, 0, "and is NOT sent to the login page (F4: no bounce loop)");

  dom = await load(makeFrame(), makeCounts(),
                   { "alvoraa_portal.frame_api.get_frame": "expired" });
  is(dom.navTried.length > 0, true,
     "a session that has ended sends the person to the login page (AC-62)");
  is(kind(dom), "loading",
     "and is not told the portal is broken on the way out");

  /* ── the sheet (US-9) ──────────────────────────────────────────────────── */

  dom = await load(makeFrame(), makeCounts());
  el(dom, "nf-profile-btn").click();
  is(dom.window.NextFrame.sheetIsOpen(), true, "the profile sheet opens");
  is(el(dom, "nf-sheet").getAttribute("role"), "dialog", "it is a dialog");
  is(el(dom, "nf-sheet").getAttribute("aria-modal"), "true", "and a modal one");
  is(dom.window.document.activeElement.id, "nf-sheet-title", "focus moves into it");
  dom.window.document.dispatchEvent(
    new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  is(dom.window.NextFrame.sheetIsOpen(), false, "Escape closes it (AC-34)");
  is(dom.window.document.activeElement.id, "nf-profile-btn",
     "and focus returns to the control that opened it");

  /* AC-75 / W1D-19: a plain manager gets no desk link at all. */
  dom = await load(makeFrame({ has_reports: true, is_manager: true, persona_rule: 3,
                               allowed_pages: ["home", "inbox", "time", "growth", "pay", "team"],
                               bottom_bar: ["home", "team", "inbox", "time"] }), makeCounts());
  dom.window.NextFrame.openProfile();
  is(el(dom, "nf-desk"), null, "a plain manager is offered no desk link (AC-75)");

  dom = await load(makeFrame(Object.assign({}, hrBase, {
    features: { goals: 1 }, switch_target: { label: "Switch to HR Core", url: "/app/hr" } })),
    makeCounts());
  dom.window.NextFrame.openProfile();
  is(el(dom, "nf-desk").textContent, "Switch to HR Core",
     "HR gets the server's own label, not the prototype's wording");
  is(el(dom, "nf-desk").getAttribute("href"), "/app/hr", "pointing where the server says");

  /* AC-18: no language row, on any persona, because no translation ships. */
  is(el(dom, "nf-sheet-body").textContent.toLowerCase().includes("language"), false,
     "there is no language row until a translation ships (AC-18)");

  /* ── the theme switch (AC-19) ──────────────────────────────────────────── */

  const head = SRC.indexOf("alvoraa-theme");
  const tokens = SRC.indexOf("--sidebar-bg");
  is(head > -1 && tokens > -1 && head < tokens, true,
     "the inline theme script comes before the design system's tokens (AC-19)");
  dom.window.NextFrame.setTheme("dark");
  is(dom.window.document.documentElement.getAttribute("data-theme"), "dark",
     "choosing Dark sets data-theme");
  is(dom.window.localStorage.getItem("alvoraa-theme"), "dark", "and keeps it on the device");
  dom.window.NextFrame.setTheme("auto");
  is(dom.window.document.documentElement.hasAttribute("data-theme"), false,
     "'Match my phone' removes it, so the media query decides");

  /* ── search (US-7) ─────────────────────────────────────────────────────── */

  dom = await load(makeFrame(), makeCounts());
  el(dom, "nf-search-btn").click();
  is(dom.window.NextFrame.sheetIsOpen(), true, "the search sheet opens");
  const offered = dom.window.NextFrame.matchingPages("").map((p) => p.route).sort();
  is(offered.join(","), menuRoutes(dom).sort().join(","),
     "the pages offered in search are exactly the pages in the menu (AC-25)");

  const NF = dom.window.NextFrame;
  is(NF.emptySearchSentence("x").includes("your own team"),
     true, "an employee is told their search covers their own team");
  NF._set(makeFrame({ is_hr: true, scope_is_store: true }), makeCounts());
  is(NF.emptySearchSentence("x").includes("your store"), true,
     "a store's HR person is told it covers their store and their own line (AC-29)");
  NF._set(makeFrame({ is_hr: true, scope_is_store: false }), makeCounts());
  is(NF.emptySearchSentence("x").includes("companies you look after"), true,
     "company-wide HR is told it covers their companies");
  NF._set(makeFrame({ has_employee: false, me: null, is_hr: false }), makeCounts());
  is(NF.emptySearchSentence("x").includes("open the pages in this list"), true,
     "somebody with no employee record is told they can open pages");

  /* ── the staff list, and what it does with a nasty job title ───────────── */

  const nasty = { employee: "HR-EMP-9", name: "Meera Rao",
                  title: "<img src=x onerror=alert(1)>", department: "Sales", image: null };
  dom = await load(
    makeFrame(Object.assign({}, hrBase, { features: { goals: 1, plan_staff_list: true } })),
    makeCounts(),
    { "alvoraa_portal.staff_api.get_staff_list": () => ({ rows: [nasty], total: 1 }) });
  dom.window.NextFrame.go("company/staff");
  await new Promise((r) => setTimeout(r, 10));
  const out = el(dom, "nf-staff-out");
  is(out.textContent.includes("Meera Rao"), true, "the staff list draws the person");
  is(out.querySelectorAll("img[src='x']").length, 0,
     "a job title of <img onerror> creates no element (AC-58)");
  is(out.textContent.includes("<img src=x onerror=alert(1)>"), true,
     "it appears as text instead");

  /* Key off: the address shows the no-permission sentence, never a blank list
     and never an error (AC-76). */
  dom = await load(makeFrame(Object.assign({}, hrBase, { features: { goals: 1 } })), makeCounts());
  dom.window.NextFrame.go("company/staff");
  is(kind(dom), "refused", "with the switch off, #company/staff shows the refusal");
  is(say(dom), dom.window.NextFrame.SAY.noPermission,
     "and it reads the same as any other refusal - not bought and not allowed look alike");

  /* ── toasts (AC-35) ────────────────────────────────────────────────────── */

  dom.window.NextFrame.toast("Saved");
  is(el(dom, "nf-toasts").getAttribute("role"), "status", "toasts are announced");
  is(el(dom, "nf-toasts").textContent.includes("Saved"), true, "and the message is there");

  console.log("\nnext frame: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

run().catch((e) => { console.error(e); process.exit(1); });
