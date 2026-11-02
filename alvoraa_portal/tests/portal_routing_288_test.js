/* ALV-288 in the browser: the address says which screen you are on, and a
   refresh comes back to it.

   Surbhi, 2 November 2026: "If I refresh the page from browser refresh button,
   it takes us to home page insted of where we were before refresh."

   Driven in jsdom against the real page and the real portal.js, with a stub
   server. Pin tests, so a bad merge that drops one fails here by name:

     - clicking a sidebar item puts that panel in the address
     - a route from CODE puts it there too, not only a click - every caller goes
       through switchPanel, which is the one place the address is written
     - a fresh page at #att-record opens Attendance Record, not Home
     - THE ONE THAT MATTERS: all 23 panels are in the page for everybody, so a
       plain employee typing #org-settings must get Home, silently - no panel,
       no sentence naming what was refused
     - and the same address DOES open for an HR login, so the check above is not
       passing because the router refuses everything
     - a malformed address lands on Home and throws nothing
     - Back moves between screens
     - slice 078's ?seat= address keeps the fragment, and leaving the seat page
       takes ?seat= with it

   Run: node alvoraa_portal/tests/portal_routing_288_test.js \
          alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const yes = (cond, m, detail) => (cond ? ok(m) : bad(m + (detail ? ": " + detail : "")));

const method = s => String(s).split(".").pop();
const settle = ms => new Promise(r => setTimeout(r, ms));

/* The page makes a dozen calls on load. Only two of them decide the sidebar,
   and therefore what the address is allowed to open. Everything else answers
   with an empty object, which is what the other jsdom suites here do. */
const BASE = {
  get_checkin_status: { no_employee: 1 },
  get_employee_dashboard: { no_employee: true },
};

function boot(hash, ctx, features) {
  const shown = [];          /* anything the page tried to say out loud */
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "http://grace.localhost/hrms-employee" + (hash || ""),
    beforeParse(w) {
      const answers = Object.assign({}, BASE, {
        get_portal_context: ctx || {},
        get_available_features: features || {},
      });
      w.fetch = (url) => Promise.resolve({
        ok: true, status: 200,
        json: () => Promise.resolve({ message: answers[method(url)] || {} }),
      });
      w.frappe = {
        call: (o) => {
          const v = answers[method(o.method)] || {};
          setTimeout(() => { o.callback && o.callback({ message: v }); o.always && o.always({}); }, 0);
          return { status: 200 };
        },
        csrf_token: "x", boot: {}, ui: {}, _messages: {},
        utils: { escape_html: s => s },
        msgprint: (m) => shown.push(String(m && m.message !== undefined ? m.message : m)),
      };
    },
  });
  dom.window.addEventListener("error", e => shown.push("ERROR " + e.message));
  return { window: dom.window, doc: dom.window.document, shown };
}

const activePanel = doc => {
  const el = doc.querySelector(".panel.active");
  return el ? el.id.replace(/^panel-/, "") : null;
};
const click = (window, el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

/* An HR login on a tenant that has bought everything: the sidebar shows
   Organisation, which is what makes #org-settings reachable at all. */
const HR_CTX = { is_hr: 1, is_manager: 1, employee: "HR-EMP-288" };
const HR_PLAN = { plan_analytics: true, plan_org_structure: true, goals: true };

(async () => {
  /* ── 1. a click puts the panel in the address ──────────────────────────── */
  {
    const { window, doc } = boot("", {}, {});
    await settle(120);
    const item = doc.querySelector('.nav-item[data-panel="attendance"]');
    if (!item) { bad("the sidebar has no Attendance item to click"); process.exit(1); }
    click(window, item);
    yes(window.location.hash === "#attendance",
        "clicking Attendance puts #attendance in the address",
        "the address reads " + JSON.stringify(window.location.hash));
    yes(activePanel(doc) === "attendance", "and the Attendance panel is the one on screen",
        "on screen: " + activePanel(doc));
  }

  /* ── 2. a route from CODE writes it too ────────────────────────────────── */
  {
    const { window } = boot("", {}, {});
    await settle(120);
    /* What the bell, the Home cards and the day strip do - switchPanel called
       with no element. If the address were written by the click handlers, these
       callers would leave it behind. */
    window.switchPanel("att-record", null);
    yes(window.location.hash === "#att-record",
        "a route from code (switchPanel with no element) writes the address as well",
        "the address reads " + JSON.stringify(window.location.hash));
  }

  /* ── 3. the complaint itself: a reload comes back ──────────────────────── */
  {
    const { doc, window } = boot("#att-record", {}, {});
    await settle(200);
    yes(activePanel(doc) === "att-record",
        "a fresh page at #att-record opens Attendance Record, not Home",
        "on screen: " + activePanel(doc));
    yes(window.location.hash === "#att-record", "and the address is left alone");
  }

  /* ── 4. the leak the router must not open ──────────────────────────────── */
  {
    /* A plain employee. Every one of the 23 panels is in their page - the
       server pastes them all in - and the only thing that has ever kept
       Organisation out of reach is that its nav item is not shown. */
    const { doc, window, shown } = boot("#org-settings", { employee: "HR-EMP-999" }, {});
    await settle(250);
    const item = doc.querySelector('.nav-item[data-panel="org-settings"]');
    yes(item && item.style.display === "none",
        "the plain employee is not offered Organisation in the sidebar",
        item ? "display is " + JSON.stringify(item.style.display) : "the item is missing");
    yes(activePanel(doc) !== "org-settings",
        "ALV-288: typing #org-settings does NOT open the panel for them",
        "on screen: " + activePanel(doc));
    yes(activePanel(doc) === "home", "they land on Home instead",
        "on screen: " + activePanel(doc));
    yes(window.location.hash === "#home", "and the refused address is replaced by #home",
        "the address reads " + JSON.stringify(window.location.hash));
    /* Silently. A sentence naming what was refused is a map of what to go
       after, and a dead end is not news to somebody who typed a guess. */
    yes(shown.length === 0, "nothing is said about the refusal, and nothing threw",
        "the page said: " + JSON.stringify(shown));
  }

  /* ── 5. and it is not refusing everybody ───────────────────────────────── */
  {
    const { doc, window } = boot("#org-settings", HR_CTX, HR_PLAN);
    await settle(250);
    yes(activePanel(doc) === "org-settings",
        "the SAME address opens Organisation for an HR login - so check 4 proves something",
        "on screen: " + activePanel(doc));
    yes(window.location.hash === "#org-settings", "and their address is left alone");
  }

  /* ── 6. a typo is not a fault worth reporting ──────────────────────────── */
  {
    const { doc, window, shown } = boot('#"]+[data-panel="org-settings', {}, {});
    await settle(250);
    yes(activePanel(doc) === "home", "a malformed address opens Home",
        "on screen: " + activePanel(doc));
    yes(window.location.hash === "#home", "and is replaced by #home",
        "the address reads " + JSON.stringify(window.location.hash));
    yes(shown.length === 0, "a malformed address throws nothing and says nothing",
        "the page said: " + JSON.stringify(shown));
  }

  /* ── 7. Back moves between screens ─────────────────────────────────────── */
  {
    const { window, doc } = boot("", {}, {});
    await settle(120);
    click(window, doc.querySelector('.nav-item[data-panel="attendance"]'));
    click(window, doc.querySelector('.nav-item[data-panel="finances"]'));
    yes(activePanel(doc) === "finances", "two clicks later, Pay is on screen",
        "on screen: " + activePanel(doc));
    window.history.back();
    await settle(120);
    yes(window.location.hash === "#attendance" && activePanel(doc) === "attendance",
        "Back returns to Attendance - the screen before, not the home page",
        "the address reads " + JSON.stringify(window.location.hash) +
        " and on screen is " + activePanel(doc));
    window.history.forward();
    await settle(120);
    yes(window.location.hash === "#finances" && activePanel(doc) === "finances",
        "Forward goes to Pay again",
        "the address reads " + JSON.stringify(window.location.hash) +
        " and on screen is " + activePanel(doc));
  }

  /* ── 8. slice 078's ?seat= address, which rebuilt the URL by hand ──────── */
  {
    const { window, doc } = boot("", HR_CTX, HR_PLAN);
    await settle(200);
    window.switchPanel("positions", null);
    window.spAddress("POS-0001");
    yes(window.location.hash === "#positions",
        "078 AC: writing the ?seat= address keeps the panel in the fragment",
        "the address reads " + JSON.stringify(window.location.hash));
    yes(/seat=POS-0001/.test(window.location.search), "and the seat is still in the query",
        "the query reads " + JSON.stringify(window.location.search));
    window.switchPanel("home", null);
    yes(!/seat=/.test(window.location.search),
        "leaving the seat page takes ?seat= with it, so a reload does not reopen the seat",
        "the query reads " + JSON.stringify(window.location.search));
    yes(activePanel(doc) === "home", "and Home is on screen");
  }

  /* ── 9. the detail screens, which have no nav item ─────────────────────── */
  {
    /* Compose, a scorecard, a review, a seat: addressed so Back can leave them,
       never restored, and - the bug this pins - never bounced off the screen by
       the router a moment after they open. */
    const { window, doc } = boot("", HR_CTX, HR_PLAN);
    await settle(200);
    window.switchPanel("notice-compose", null);
    await settle(80);
    yes(activePanel(doc) === "notice-compose",
        "a detail screen with no nav item STAYS on screen after its address is written",
        "on screen: " + activePanel(doc));
    yes(window.location.hash === "#notice-compose", "and it does have an address",
        "the address reads " + JSON.stringify(window.location.hash));
    window.history.back();
    await settle(120);
    yes(activePanel(doc) === "home",
        "Back leaves it for the screen that opened it",
        "on screen: " + activePanel(doc));
  }
  {
    const { doc } = boot("#notice-compose", HR_CTX, HR_PLAN);
    await settle(250);
    yes(activePanel(doc) === "home",
        "but a COLD #notice-compose opens Home - there is nothing written to come back to",
        "on screen: " + activePanel(doc));
  }

  console.log(`\n### ALV-288 routing: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
