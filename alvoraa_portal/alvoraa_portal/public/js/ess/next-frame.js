/* Slice 034, Wave 1: the portal frame.
 *
 * The rail, the top bar, the bottom bar, routes, focus, the shared sheet, the
 * toast strip, the bell, search, the theme switch and the five states.
 *
 * Four rules run through all of it.
 *
 * **Two start-up calls, and no timers** (US-2, AC-7). `get_frame` and
 * `get_nav_counts` go out together. The menu is drawn once, from one answer, so
 * nothing appears late or goes missing. Today's page makes three calls that
 * race, which is why an item could be absent on a tenant that owns it.
 *
 * **An entry a person cannot use is not drawn at all** (AC-6). No greyed-out
 * items, no disabled attributes, nothing that fails when tapped.
 *
 * **Hiding a menu entry is not a permission.** Every screen behind every entry
 * checks its own caller on the server. This file decides what to DRAW; it never
 * decides what anybody may READ. A refusal reads the same whether the cause is
 * "your tenant has not bought this" or "you are not allowed this" - a menu that
 * says which is a map of what to go after.
 *
 * **A count equals the list it links to.** The bell, the Inbox entry and the
 * Inbox button all show one number, from one call. Where a screen is capped the
 * row says so rather than quietly showing fewer.
 */

(function () {
  "use strict";

  var PORTAL = "alvoraa_portal";
  var FRAME = PORTAL + ".frame_api.get_frame";
  var COUNTS = PORTAL + ".inbox_api.get_nav_counts";
  var STAFF = PORTAL + ".staff_api.get_staff_list";
  var PEOPLE = "hrms.alvoraa_org_structure.api.search_people";

  /* Section 6 of the spec, word for word. They live in one object because a
     sentence that appears in two places drifts in one of them, and because
     wrapping them for translation later is then one edit. */
  var SAY = {
    pageFailed: function (code) {
      return __("The portal could not load. Try again. If it keeps happening, tell HR this code: {0}.", [code]);
    },
    countsFailed: __("The waiting list could not load. Try again."),
    searchFailed: __("People search is not answering. You can still open pages from this list."),
    allClear: __("All clear."),
    noPermission: __("This page is not part of your access. Ask HR if you think it should be."),
    loading: __("Loading…"),
    noEmployee: __("Your account is not linked to an employee record."),
    settingsReadOnly: __("Only company-wide HR can change these settings."),
    /* One sentence per scope, and the scope named is the one the SERVER
       enforces - not a friendlier version of it (AC-29). */
    emptySearch: {
      line: function (term) {
        return __("Nothing matches \"{0}\". You can find your own team and the pages you can open.", [term]);
      },
      company: function (term) {
        return __("Nothing matches \"{0}\". You can find people in the companies you look after.", [term]);
      },
      store: function (term) {
        return __("Nothing matches \"{0}\". You can find people in your store and anyone who reports to you.", [term]);
      },
      none: function (term) {
        return __("Nothing matches \"{0}\". You can open the pages in this list.", [term]);
      }
    }
  };

  /* Section 5's parts, in the Inbox page's order, with the sentence each row
     says. `n` is the count; the sentence is built per row so that a plural is
     a whole sentence and never a letter glued on the end (i18n). */
  var INBOX_ROWS = {
    leave_approvals: function (n) { return __("{0} leave requests to approve", [n]); },
    goal_updates: function (n) { return __("{0} goal or KPI updates to approve", [n]); },
    attendance_fixes: function (n) { return __("{0} attendance fixes to decide", [n]); },
    shift_requests: function (n) { return __("{0} shift changes to approve", [n]); },
    policies: function (n) { return __("{0} policies to read and accept", [n]); },
    my_requests: function (n) { return __("{0} of your requests are waiting", [n]); }
  };

  /* Section 4's routes, grouped the way the rail groups them.
   *
   * `page` is the top-level page key the server answers with in
   * `allowed_pages` and `bottom_bar`. `when` is an EXTRA condition on top of
   * that page being allowed - a tab inside a group that the tenant has not
   * bought.
   *
   * The missing-key rule (section 3): an absent `plan_*` key means "not
   * answered yet", so the item shows - `!== false`. Three keys do not follow
   * it, and each has its reason written beside it. */
  var MENU = [
    { key: "me", label: null, items: [
      { route: "home", page: "home", title: __("Home") },
      { route: "inbox", page: "inbox", title: __("Inbox"), count: "total" }
    ] },
    { key: "time", label: __("Time"), items: [
      { route: "time", page: "time", title: __("Attendance & leave") },
      { route: "time/days", page: "time", title: __("My days") },
      { route: "time/insights", page: "time", title: __("Insights") },
      { route: "time/shift", page: "time", title: __("Change shift") },
      { route: "time/fix", page: "time", title: __("Fix attendance") }
    ] },
    { key: "pay", label: __("Pay"), items: [
      /* Salary is the one plan key where ABSENT hides, because showing
         payslips a tenant did not buy is worse than hiding a page they did. */
      { route: "pay", page: "pay", title: __("My pay"),
        when: function (f) { return !!f.features.plan_payroll; } },
      /* `expenses` is a required feature on every plan, so the Pay group
         always has something in it (W1D-01, AC-1). */
      { route: "pay/expenses", page: "pay", title: __("Expenses") },
      /* Not `plan_*` keys. They are set separately and today's page reads them
         straight, so absent already behaves as false - and the frame keeps
         exactly that, which is what a tenant sees today (AC-45). */
      { route: "pay/encashment", page: "pay", title: __("Leave encashment"),
        when: function (f) { return !!f.features.leave_encashment; } },
      { route: "pay/advance", page: "pay", title: __("Request advance"),
        when: function (f) { return !!f.features.advance_request; } }
    ] },
    { key: "growth", label: __("Growth"), items: [
      { route: "growth", page: "growth", title: __("Goals & reviews") },
      { route: "growth/review", page: "growth", title: __("Self-review") }
    ] },
    { key: "team", label: __("Team"), items: [
      { route: "team", page: "team", title: __("My team") }
    ] },
    { key: "company", label: __("Company"), items: [
      { route: "company/analytics", page: "company", title: __("HR analytics"),
        when: function (f) { return f.is_hr && f.features.plan_analytics !== false; } },
      { route: "company/data", page: "company", title: __("Data to review"),
        when: function (f) { return f.is_hr && f.features.plan_analytics !== false; },
        count: "review" },
      { route: "company/reviews", page: "company", title: __("Reviews (HR)"),
        when: function (f) { return f.is_hr && !!f.features.goals; } },
      { route: "company/policies", page: "company", title: __("Policies"),
        when: function (f) { return f.features.plan_policy_library !== false; },
        count: "policies" },
      { route: "company/people", page: "company", title: __("People"),
        when: function (f) { return f.features.plan_org_structure !== false; } },
      /* W1D-21 / SEC-16. An opt-in key: absent means the tenant was never given
         it, and an entitlement read that failed leaves every key absent - so
         absent must HIDE, or a failed read hands out an unsold screen. The org
         chart above keeps `plan_org_structure`; the two are independent, which
         is the whole point of the split. The server refuses the endpoint as
         well, because a hidden entry is not a permission. */
      { route: "company/staff", page: "company", title: __("Staff list"),
        when: function (f) { return f.is_hr && f.features.plan_staff_list === true; } },
      { route: "company/settings", page: "company", title: __("Org settings"),
        when: function (f) { return f.is_hr; } }
    ] }
  ];

  /* Deep pages: reachable by address, not listed in the menu. The group is a
     link back (AC-13). */
  var DEEP = [
    { route: "team/person", page: "team", title: __("Person"), backTo: "team" }
  ];

  /* The bottom bar's labels. The server decides WHICH keys are in the bar and
     in what order (frame_api._bottom_bar); this is only what each one is
     called. More is always last and is the browser's job, never the server's. */
  var TAB_LABEL = {
    home: __("Home"), inbox: __("Inbox"), time: __("Time"), growth: __("Goals"),
    pay: __("Pay"), team: __("Team"), company: __("Company")
  };

  /* ── state ───────────────────────────────────────────────────────────────── */

  var frame = null;       /* get_frame's answer, or null until it lands */
  var counts = null;      /* get_nav_counts' answer, or null */
  var countsFailed = false;
  var current = null;     /* the route being shown */
  var lastFocus = null;   /* what opened the sheet, so it can be given back */

  /* ── small helpers ───────────────────────────────────────────────────────── */

  function el(id) { return document.getElementById(id); }

  /* Everything the server returns goes through this before it reaches
     innerHTML. A designation of `<img src=x onerror=alert(1)>` has to appear as
     text and create no element (SEC-10, AC-58). */
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* Frappe's own translator when the page has one, and the English string when
     it does not. Website pages ship an empty `frappe._messages`, so this is
     English today either way - what matters is that every string goes through
     one door, so shipping a translation later is a build step and not a rewrite
     of this file (section 14). */
  function __(text, args) {
    var out = (window.frappe && frappe._ && typeof frappe._ === "function")
      ? frappe._(text) : text;
    if (args) {
      for (var i = 0; i < args.length; i++) {
        out = out.split("{" + i + "}").join(String(args[i]));
      }
    }
    return out;
  }

  /* --- one door for every call this frame makes ---------------------------

     It deliberately does NOT use frappe.call.

     A website page loads `frappe-web.bundle.js`, and the `frappe.call` in that
     bundle is website.js's own version, not the desk one. That version never
     calls `opts.error` - its `process_response` knows only `callback`,
     `success` and `always`. Proved in a real browser against a real session on
     2026-09-24: with a stale CSRF token only `always` fired, never `callback`
     and never `error`. A promise built on it would never settle, so the frame
     would sit on "Loading" for ever, with nothing in any log.

     A plain POST to /api/method/ hands us the status code and the exception
     type, which is what the two things below both need:

       - the stale-token retry the live portal has carried since a desk page
         opening in another tab started breaking every open portal tab. It is
         the same fault `hrms_employee.py` mints a token for, and the frame had
         only half the cure.
       - an honest signed-out test, so a real refusal is not read as a dead
         session and a dead session is not read as a broken page.

     POST rather than GET because a search term is somebody's name and does not
     belong in a URL or a proxy log (PRIV-5). */

  function csrfToken() {
    var c = (window.frappe && window.frappe.csrf_token) || "";
    /* Frappe prints Python's None into the page as the string "None", which is
       truthy here. Sending nothing is better than sending that: Frappe skips
       the check for a session with no token, and refuses a wrong one. */
    return (c === "None" || c === "null" || c === "undefined") ? "" : c;
  }

  /* The token is fixed when the page is built, so a tab left open across a
     session change holds the old one for as long as it stays open and nothing
     would ever correct it. Re-reading this page is how we find out what it is
     now. It is set globally, so anything else on the page is mended by the
     same round trip. */
  function refreshCsrf() {
    return fetch(window.location.pathname, { credentials: "same-origin" })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var m = html.match(/<script>frappe\.csrf_token\s*=\s*"([^"]*)"/);
        var tok = m ? m[1] : "";
        if (!tok || tok === "None") { return ""; }
        if (!window.frappe) { window.frappe = {}; }
        window.frappe.csrf_token = tok;
        return tok;
      })
      .catch(function () { return ""; });
  }

  /* The server's own sentence where there is one, so a refusal reads the same
     here as it does everywhere else. The status and the exception type travel
     with it, because `isSignedOut` needs them. */
  function apiError(data, res) {
    var msg = "";
    try { msg = JSON.parse(JSON.parse(data._server_messages)[0]).message; } catch (e) {}
    if (!msg && data && typeof data.exc === "string") {
      try { msg = JSON.parse(data.exc)[0].trim().split("\n").pop(); } catch (e) {}
    }
    var err = new Error(msg || (res && res.statusText) || "Request failed");
    err.status = res ? res.status : 0;
    err.exc_type = data ? data.exc_type : undefined;
    return err;
  }

  function send(method, args) {
    var headers = { "Content-Type": "application/json" };
    var token = csrfToken();
    if (token) { headers["X-Frappe-CSRF-Token"] = token; }
    return fetch("/api/method/" + method, {
      method: "POST",
      headers: headers,
      credentials: "same-origin",
      body: JSON.stringify(args || {})
    }).then(function (res) {
      return res.text().then(function (text) {
        var data = {};
        try { data = JSON.parse(text); } catch (e) { data = {}; }
        return { res: res, data: data };
      });
    });
  }

  /* A token the server no longer recognises. Frappe answers 400 with
     CSRFTokenError and the sentence "Invalid Request". Both are checked: the
     sentence alone also matches other bad requests, and the type alone is not
     carried through every proxy. */
  function isStaleToken(res, data) {
    if (data && data.exc_type === "CSRFTokenError") { return true; }
    var said = String((data && (data.message || data._server_messages)) || "");
    return res.status === 400 && /invalid request/i.test(said);
  }

  function api(method, args) {
    return new Promise(function (resolve, reject) {
      send(method, args).then(function (out) {
        if (out.res.ok && !out.data.exc_type) { resolve(out.data.message); return; }
        if (!isStaleToken(out.res, out.data)) {
          reject(apiError(out.data, out.res));
          return;
        }
        /* One retry, with a token read fresh from the server. If that one
           fails too, the answer is a real refusal and not a stale token. */
        refreshCsrf().then(function (tok) {
          if (!tok) { reject(apiError(out.data, out.res)); return; }
          send(method, args).then(function (again) {
            if (again.res.ok && !again.data.exc_type) { resolve(again.data.message); }
            else { reject(apiError(again.data, again.res)); }
          }).catch(reject);
        }).catch(reject);
      }).catch(reject);
    });
  }

  function initials(name) {
    if (!name) { return "?"; }
    return name.trim().split(/\s+/).map(function (w) { return w[0]; })
      .slice(0, 2).join("").toUpperCase();
  }

  /* A short reference a person can read out, and an Error Log entry can be
     found by. It holds no personal data - the time and four characters of the
     clock, nothing about who or what (AC-33). */
  function errorCode() {
    var now = new Date();
    var hhmm = ("0" + now.getHours()).slice(-2) + ":" + ("0" + now.getMinutes()).slice(-2);
    return hhmm + " · " + now.getTime().toString(36).slice(-4).toUpperCase();
  }

  /* ── toasts (AC-35) ──────────────────────────────────────────────────────── */

  function toast(msg, kind) {
    var wrap = el("nf-toasts");
    if (!wrap) { return; }
    var node = document.createElement("div");
    node.className = "nf-toast";
    if (kind) { node.setAttribute("data-kind", kind); }
    node.textContent = msg;
    wrap.appendChild(node);
    window.setTimeout(function () { node.remove(); }, 4000);
    return node;
  }

  /* ── the five states ─────────────────────────────────────────────────────── */

  /* One box, one state at a time. `kind` is one of loading, empty, refused,
     error, page-error - and it is written to the DOM as an attribute so a test
     can ask which state is on screen without reading the sentence. */
  function showState(kind, say, retry) {
    var box = el("nf-state");
    var screens = el("nf-screens");
    box.setAttribute("data-kind", kind);
    el("nf-state-say").textContent = say;
    var button = el("nf-state-retry");
    button.hidden = !retry;
    button.onclick = retry || null;
    box.hidden = false;
    screens.hidden = true;
  }

  function showScreen(html) {
    el("nf-state").hidden = true;
    var screens = el("nf-screens");
    screens.innerHTML = html;
    screens.hidden = false;
    return screens;
  }

  /* ── the rail ────────────────────────────────────────────────────────────── */

  function itemIsOffered(item) {
    if (!frame.allowedSet[item.page]) { return false; }
    return item.when ? !!item.when(frame) : true;
  }

  function countFor(kind) {
    if (!counts) { return 0; }
    if (kind === "total") { return counts.total; }
    if (kind === "policies") { return partCount("policies"); }
    if (kind === "review") { return frame.review_open_count || 0; }
    return 0;
  }

  function partCount(key) {
    if (!counts) { return 0; }
    for (var i = 0; i < counts.parts.length; i++) {
      if (counts.parts[i].key === key) { return counts.parts[i].count; }
    }
    return 0;
  }

  function drawMenu() {
    var html = "";
    MENU.forEach(function (group) {
      var items = group.items.filter(itemIsOffered);
      if (!items.length) { return; }
      if (group.label) {
        html += '<div class="nf-group-head">' + esc(group.label) + "</div>";
      }
      items.forEach(function (item) {
        var n = item.count ? countFor(item.count) : 0;
        html += '<a class="nf-item" href="#' + esc(item.route) + '" data-route="' + esc(item.route) + '">'
          + '<span class="nf-item-label">' + esc(item.title) + "</span>"
          /* A badge of zero shows no number at all (AC-61). A "0" beside a
             menu entry reads as a thing to go and look at. */
          + (n > 0 ? '<span class="nf-count">' + esc(n) + "</span>" : "")
          + "</a>";
      });
    });
    el("nf-menu").innerHTML = html;
  }

  function drawBottomBar() {
    var html = "";
    frame.bottom_bar.forEach(function (page) {
      var route = defaultRouteFor(page);
      var n = page === "inbox" ? countFor("total") : 0;
      html += '<a class="nf-tab" href="#' + esc(route) + '" data-page="' + esc(page) + '">'
        + (n > 0 ? '<span class="nf-badge">' + esc(n) + "</span>" : "")
        + '<span class="nf-tab-label">' + esc(TAB_LABEL[page] || page) + "</span>"
        + "</a>";
    });
    /* More is always last, and only when there is something the four buttons
       do not already reach (B4). */
    if (frame.allowed_pages.length > frame.bottom_bar.length) {
      html += '<button type="button" class="nf-tab" id="nf-more">'
        + '<span class="nf-tab-label">' + esc(__("More")) + "</span></button>";
    }
    el("nf-bottom").innerHTML = html;
    var more = el("nf-more");
    if (more) { more.onclick = function () { setRail(true); }; }
  }

  /* Which address a top-level page opens.
   *
   * Pay is the one that is not itself: `#pay` is the salary tab, which does not
   * exist without payroll, so on those tenants the Pay button opens
   * `#pay/expenses` instead and nothing in the menu points at `#pay` (AC-44).
   * Typing `#pay` there still shows the no-permission sentence, because an old
   * bookmark must land somewhere honest. */
  function defaultRouteFor(page) {
    if (page === "pay" && !(frame.features.plan_payroll)) { return "pay/expenses"; }
    if (page === "company") { return firstCompanyRoute(); }
    return page;
  }

  /* The Company button opens the first of these this person may open (section
     2): HR analytics, Reviews (HR), Policies, People, Org settings. */
  function firstCompanyRoute() {
    var order = ["company/analytics", "company/reviews", "company/policies",
                 "company/people", "company/staff", "company/settings"];
    var offered = allRoutes().filter(itemIsOffered).map(function (i) { return i.route; });
    for (var i = 0; i < order.length; i++) {
      if (offered.indexOf(order[i]) !== -1) { return order[i]; }
    }
    return "home";
  }

  function allRoutes() {
    var out = [];
    MENU.forEach(function (g) {
      g.items.forEach(function (item) {
        out.push({ route: item.route, page: item.page, title: item.title,
                   when: item.when, group: g.label });
      });
    });
    DEEP.forEach(function (d) { out.push(d); });
    return out;
  }

  function findRoute(hash) {
    var all = allRoutes();
    for (var i = 0; i < all.length; i++) {
      if (all[i].route === hash) { return all[i]; }
    }
    return null;
  }

  /* ── the rail's open and closed state on a phone ─────────────────────────── */

  function setRail(open) {
    var root = el("nf-root");
    root.setAttribute("data-nf-rail", open ? "open" : "closed");
    el("nf-menu-btn").setAttribute("aria-expanded", open ? "true" : "false");
    el("nf-scrim").hidden = !open;
    /* The rail is taken out of the tab order by `visibility: hidden` in the
       stylesheet's phone block, driven by the attribute above - not by an
       `hidden` set here, which would hide it on a desktop too. */
    if (open) {
      var first = el("nf-menu").querySelector(".nf-item");
      if (first) { first.focus(); }
    }
  }

  /* ── routing (US-4) ──────────────────────────────────────────────────────── */

  function currentHash() {
    var raw = String(window.location.hash || "").replace(/^#/, "");
    return raw || "home";
  }

  function go(hash) {
    /* The hash is updated synchronously; the `hashchange` event is not. So the
       route is drawn here rather than waiting for the event, and the event
       handler simply draws it again - `route()` is safe to run twice on the
       same address. Without this the page lags one click behind whenever
       something other than a link changes the address, which is how the bell
       and the More button move. */
    if (currentHash() !== hash) { window.location.hash = "#" + hash; }
    route();
  }

  function route() {
    if (!frame) { return; }
    var hash = currentHash();
    var found = findRoute(hash);

    /* An address nobody recognises opens Home and leaves no error behind
       (AC-14). A typo is not a fault worth telling somebody about. */
    if (!found) {
      window.location.replace("#home");
      return;
    }

    current = found;
    setRail(false);
    setTitle(found);
    markCurrent(found);

    if (!itemIsOffered(found)) {
      /* The same sentence whichever the cause - not bought, or not allowed.
         Two different sentences would be a map of what to go after (AC-30). */
      showState("refused", SAY.noPermission);
      focusHeading();
      return;
    }
    drawScreen(found);
    focusHeading();
  }

  function setTitle(found) {
    var group = el("nf-group");
    var page = el("nf-page");
    page.textContent = found.title;
    var groupLabel = found.group || null;
    if (found.backTo) {
      var parent = findRoute(found.backTo);
      groupLabel = parent ? parent.title : groupLabel;
      group.setAttribute("href", "#" + found.backTo);
    } else {
      group.setAttribute("href", "#home");
    }
    group.textContent = groupLabel || "";
    /* Back is offered on the deep pages, where there is somewhere named to go
       back to. Elsewhere the browser's own Back is the right control and a
       second one beside it is noise. */
    el("nf-back").hidden = !found.backTo;
    document.title = found.title + " · " + (frame.tenantName || __("Employee portal"));
  }

  function markCurrent(found) {
    var nodes = document.querySelectorAll("[data-route], .nf-tab[data-page]");
    Array.prototype.forEach.call(nodes, function (node) {
      var isHere = node.getAttribute("data-route") === found.route
        || (node.getAttribute("data-page") && node.getAttribute("data-page") === found.page
            && node.getAttribute("href") === "#" + found.route);
      if (isHere) { node.setAttribute("aria-current", "page"); }
      else { node.removeAttribute("aria-current"); }
    });
  }

  /* After a page change, focus moves to the page heading (AC-15). Without it a
     screen reader stays where the last click was and reads nothing, and a
     keyboard user's next Tab starts from the top of the document. */
  function focusHeading() {
    var heading = el("nf-page");
    if (heading && heading.focus) { heading.focus(); }
  }

  /* ── the screens the frame itself owns ───────────────────────────────────── */

  /* Slice 042 (Wave 2) added the seam below. Home and Inbox are their own
     static files - `next-home.js` and `next-inbox.js` - because OPS-31 made
     splitting free and because two sessions building two panels should not meet
     in one file. A panel registers itself here; the frame keeps the routing,
     the states, the toasts and the counts.

     `panels` is written at load time by a file the page itself pulls in, never
     by anything a caller sends, and every panel still draws into the same
     `showScreen`, so the escaping and the state box stay in one place. */
  var panels = {};

  function drawScreen(found) {
    /* Home for somebody with no Employee record is answered HERE, before any
       panel is asked. Two reasons: the answer is already known, so asking the
       server for a page of empty cards is a call nobody needs; and a person who
       has done nothing wrong gets their one plain line immediately rather than
       a loading state first (AC-63, 042 AC-37). */
    if (found.route === "home" && !frame.has_employee) { return drawHome(); }
    if (panels[found.route]) { return panels[found.route](panelContext(found)); }
    if (found.route === "inbox") { return drawInbox(); }
    if (found.route === "company/staff") { return drawStaffList(); }
    if (found.route === "home") { return drawHome(); }
    if (found.route === "company/settings") { return drawOrgSettingsNote(); }
    return drawPlaceholder(found);
  }

  /* Everything a panel is allowed to use, handed to it rather than reached for.
     A panel gets no way to write a filter, decide a permission or change the
     counts - it asks the server and draws the answer. */
  function panelContext(found) {
    return {
      route: found,
      frame: frame,
      showScreen: showScreen,
      showState: showState,
      esc: esc,
      __: __,
      api: api,
      toast: toast,
      initials: initials,
      errorCode: errorCode,
      SAY: SAY,
      /* AC-13. After a decision the counts are RE-READ from the server. The
         browser never decrements a number it is holding: a number worked out in
         two places is how the badge and the list come to disagree. */
      reloadCounts: function () { return loadCounts(true); },
      go: go
    };
  }

  function drawHome() {
    if (!frame.has_employee) {
      /* AC-63. Asha signs in and gets a plain line, not a wall of errors. */
      return showScreen('<section class="nf-screen"><p class="nf-screen-note">'
        + esc(SAY.noEmployee) + "</p></section>");
    }
    return drawPlaceholder(findRoute("home"));
  }

  function drawOrgSettingsNote() {
    /* AC-67 / W1D-03. A store's HR person and an HR User read these settings;
       they do not save them. The flag comes from the server, which is also
       what `set_org_setting` enforces - so the button and the endpoint cannot
       drift apart. */
    var line = frame.may_save_settings ? "" :
      '<p class="nf-screen-note">' + esc(SAY.settingsReadOnly) + "</p>";
    return showScreen('<section class="nf-screen">' + line
      + '<p class="nf-screen-note">' + esc(waveNote(__("Org settings"))) + "</p></section>");
  }

  function waveNote(title) {
    return __("{0} keeps the screen it has today. Wave 1 builds the frame around it; the screen itself arrives in a later wave.", [title]);
  }

  function drawPlaceholder(found) {
    return showScreen('<section class="nf-screen"><p class="nf-screen-note">'
      + esc(waveNote(found.title)) + "</p></section>");
  }

  /* The Inbox page (AC-23). One row per part that has something, with section
     5's wording and link. A part with nothing is not shown; with nothing at all
     it says "All clear". The rows hold numbers only - no names, no reasons, no
     document ids, because that is all the endpoint returns. */
  function drawInbox() {
    if (countsFailed) {
      return showState("error", SAY.countsFailed, function () { loadCounts(true); });
    }
    if (!counts) { return showState("loading", SAY.loading); }
    var rows = counts.parts.filter(function (p) { return p.count > 0; });
    if (!rows.length) { return showState("empty", SAY.allClear); }
    var html = '<section class="nf-screen"><ul class="nf-people">';
    rows.forEach(function (part) {
      var say = INBOX_ROWS[part.key] ? INBOX_ROWS[part.key](part.count) : String(part.count);
      /* Where the screen behind the row is capped and the count is above the
         cap, the row says so. A count that matched a shorter list would be the
         one thing worse than no count (section 5, N3). */
      var capped = part.capped
        ? '<span class="nf-person-sub">'
          + esc(__("Showing the first {0} of {1} on that screen.", [part.cap, part.count]))
          + "</span>"
        : "";
      html += '<li class="nf-person"><a class="nf-sheet-row" href="' + esc(part.route) + '">'
        + '<span><span class="nf-person-name">' + esc(say) + "</span>" + capped + "</span></a></li>";
    });
    html += "</ul></section>";
    return showScreen(html);
  }

  /* The staff list (W1D-21, SEC-16). A plain searchable list of name, job
     title, department and photo. The switch is checked on the SERVER as well -
     an HR user on a tenant without the feature who calls the endpoint by hand
     is refused, because a hidden menu entry is not a permission. */
  function drawStaffList() {
    var screens = showScreen(
      '<section class="nf-screen">'
      + '<div class="nf-search-row">'
      + '<label class="nf-sr" for="nf-staff-q">' + esc(__("Search the staff list")) + "</label>"
      + '<input class="nf-input" id="nf-staff-q" type="search" autocomplete="off"'
      + ' placeholder="' + esc(__("Search by name")) + '">'
      + "</div>"
      + '<div id="nf-staff-out" role="status" aria-live="polite"></div>'
      + "</section>");
    var input = el("nf-staff-q");
    var out = el("nf-staff-out");
    var seq = 0;

    function load(term) {
      var mine = ++seq;
      out.innerHTML = '<p class="nf-screen-note">' + esc(SAY.loading) + "</p>";
      api(STAFF, { q: term || "", start: 0 }).then(function (data) {
        /* An answer that arrived after a newer one was asked for is thrown
           away, or a slow first keystroke overwrites a fast second one. */
        if (mine !== seq) { return; }
        renderPeople(out, data, term);
      }).catch(function () {
        if (mine !== seq) { return; }
        out.innerHTML = '<p class="nf-screen-note">' + esc(SAY.noPermission) + "</p>";
      });
    }

    var timer = null;
    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      var term = input.value.trim();
      /* Under two letters is not a search, and the server says so too. */
      timer = window.setTimeout(function () { load(term.length >= 2 ? term : ""); }, 200);
    });
    load("");
    return screens;
  }

  function renderPeople(out, data, term) {
    var rows = (data && data.rows) || [];
    if (!rows.length) {
      out.innerHTML = '<p class="nf-screen-note">' + esc(emptySearchSentence(term || "")) + "</p>";
      return;
    }
    var html = '<ul class="nf-people">';
    rows.forEach(function (row) { html += personRow(row); });
    html += "</ul>";
    if (data && data.total && data.total > rows.length) {
      /* The same rule as the Inbox: if the list is cut, say so. */
      html += '<p class="nf-more">'
        + esc(__("Showing the first {0} of {1}.", [rows.length, data.total])) + "</p>";
    }
    out.innerHTML = html;
  }

  function personRow(row) {
    /* A missing photo, and a photo whose address is broken, both fall back to
       initials (AC-27). `onerror` removes the image, and the initials are
       behind it rather than instead of it, so nothing has to be re-rendered. */
    var mark = '<span class="nf-avatar">' + esc(initials(row.name))
      + (row.image ? '<img src="' + esc(row.image) + '" alt="" onerror="this.remove()">' : "")
      + "</span>";
    var sub = [row.title, row.department].filter(Boolean).join(" · ");
    return '<li class="nf-person">' + mark
      + "<span><span class=\"nf-person-name\">" + esc(row.name) + "</span>"
      + (sub ? '<br><span class="nf-person-sub">' + esc(sub) + "</span>" : "")
      + "</span></li>";
  }

  /* The sentence must match the scope the SERVER actually enforces (AC-29). */
  function emptySearchSentence(term) {
    if (!frame.has_employee && !frame.is_hr) { return SAY.emptySearch.none(term); }
    if (frame.is_hr) {
      return frame.scope_is_store ? SAY.emptySearch.store(term) : SAY.emptySearch.company(term);
    }
    return SAY.emptySearch.line(term);
  }

  /* ── the shared sheet (US-9, AC-34) ──────────────────────────────────────── */

  function openSheet(title, bodyHtml, onOpen, opener) {
    /* The control that opened it, so focus can be given back on close. Passed
       in rather than read from `document.activeElement`: a click does not
       always leave focus on the button it hit, and a sheet that hands focus
       back to the wrong place is worse than one that hands it to the top. */
    lastFocus = opener || document.activeElement;
    el("nf-sheet-title").textContent = title;
    el("nf-sheet-body").innerHTML = bodyHtml;
    el("nf-sheet-wrap").hidden = false;
    el("nf-sheet-title").focus();
    if (onOpen) { onOpen(el("nf-sheet-body")); }
  }

  function closeSheet() {
    if (el("nf-sheet-wrap").hidden) { return; }
    el("nf-sheet-wrap").hidden = true;
    el("nf-sheet-body").innerHTML = "";
    /* Focus goes back to the control that opened it, or a keyboard user is
       dropped at the top of the document with no idea where they were. */
    if (lastFocus && lastFocus.focus) { lastFocus.focus(); }
    lastFocus = null;
  }

  function sheetIsOpen() { return !el("nf-sheet-wrap").hidden; }

  /* Focus stays inside the sheet while it is open. Without this, Tab walks out
     into the page behind it, which is still there and still clickable. */
  function trapFocus(event) {
    if (!sheetIsOpen() || event.key !== "Tab") { return; }
    var sheet = el("nf-sheet");
    var able = sheet.querySelectorAll(
      'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (!able.length) { return; }
    var first = able[0];
    var last = able[able.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }

  /* ── search (US-7) ───────────────────────────────────────────────────────── */

  function openSearch(opener) {
    openSheet(__("Search"),
      '<label class="nf-sr" for="nf-q">' + esc(__("Search people and pages")) + "</label>"
      + '<input class="nf-input" id="nf-q" type="search" autocomplete="off"'
      + ' placeholder="' + esc(__("Search people and pages")) + '">'
      + '<div id="nf-q-out" role="status" aria-live="polite"></div>',
      function () {
        var input = el("nf-q");
        input.focus();
        var timer = null;
        var seq = 0;
        function run() {
          var term = input.value.trim();
          var out = el("nf-q-out");
          var pages = matchingPages(term);
          if (term.length < 2) {
            /* Under two letters returns no people. The pages still list,
               because a menu that only works once you have typed enough is a
               worse menu (AC-28). */
            out.innerHTML = pagesHtml(pages);
            return;
          }
          var mine = ++seq;
          api(PEOPLE, { q: term, limit: 12 }).then(function (rows) {
            if (mine !== seq) { return; }
            out.innerHTML = peopleHtml(rows || [], term) + pagesHtml(pages);
          }).catch(function () {
            if (mine !== seq) { return; }
            /* When people search fails the sheet says so and STILL lists the
               pages (AC-60). Half a working search beats a blank sheet. */
            out.innerHTML = '<p class="nf-sheet-say">' + esc(SAY.searchFailed) + "</p>"
              + pagesHtml(pages);
          });
        }
        input.addEventListener("input", function () {
          window.clearTimeout(timer);
          timer = window.setTimeout(run, 200);
        });
        run();
      }, opener);
  }

  /* The pages offered in search are exactly the pages in this person's menu -
     one list, filtered one way (AC-25). */
  function matchingPages(term) {
    var lower = term.toLowerCase();
    return allRoutes().filter(function (item) {
      return !item.backTo && itemIsOffered(item)
        && (!term || item.title.toLowerCase().indexOf(lower) !== -1);
    });
  }

  function pagesHtml(pages) {
    if (!pages.length) { return ""; }
    var html = '<div class="nf-sheet-head-sm">' + esc(__("Pages")) + "</div>";
    pages.forEach(function (page) {
      html += '<a class="nf-sheet-row" href="#' + esc(page.route) + '" data-nf-sheet-go>'
        + esc(page.title) + "</a>";
    });
    return html;
  }

  function peopleHtml(rows, term) {
    if (!rows.length) {
      return '<p class="nf-sheet-say">' + esc(emptySearchSentence(term)) + "</p>";
    }
    var html = '<div class="nf-sheet-head-sm">' + esc(__("People")) + "</div>";
    rows.forEach(function (row) {
      var sub = [row.title, row.department].filter(Boolean).join(" · ");
      var mark = '<span class="nf-avatar">' + esc(initials(row.name))
        + (row.image ? '<img src="' + esc(row.image) + '" alt="" onerror="this.remove()">' : "")
        + "</span>";
      /* A person result opens the org chart on that person where the tenant
         has it; where it does not, the row is not a link at all rather than a
         link to a page that refuses (AC-27). */
      var open = frame.features.plan_org_structure !== false;
      var body = mark + "<span><span class=\"nf-person-name\">" + esc(row.name) + "</span>"
        + (sub ? '<br><span class="nf-person-sub">' + esc(sub) + "</span>" : "") + "</span>";
      html += open
        ? '<a class="nf-sheet-row" href="#company/people" data-nf-sheet-go>' + body + "</a>"
        : '<div class="nf-sheet-row">' + body + "</div>";
    });
    return html;
  }

  /* ── the profile sheet (US-5) ────────────────────────────────────────────── */

  function openProfile(opener) {
    var me = frame.me || {};
    /* The Employee designation, or no role line at all when it is blank - and
       the User's full name with no role line when there is no Employee record
       (AC-17). An empty line reads as a thing that failed to load. */
    var roleLine = me.designation
      ? '<div class="nf-who-role">' + esc(me.designation) + "</div>" : "";
    var html = '<div class="nf-who"><div class="nf-who-name">'
      + esc(me.employee_name || frame.user_full_name || frame.user) + "</div>"
      + roleLine + "</div>";

    html += '<a class="nf-sheet-row" href="/me">' + esc(__("My account")) + "</a>";

    /* The desk link appears only when the SERVER returns a target, with the
       server's own label (W1D-19, AC-75). The prototype offered "Switch to the
       full desk" to every manager; the code never did, and a plain manager
       gets no link at all. The prototype was wrong, not the code. */
    if (frame.switch_target && frame.switch_target.url) {
      html += '<a class="nf-sheet-row" id="nf-desk" href="' + esc(frame.switch_target.url) + '">'
        + esc(frame.switch_target.label) + "</a>";
    }
    /* Tenant admin is for control-plane operators. A tenant's own System
       Manager is not one, and /alvoraa-admin refuses them - so offering it
       would only be a door that does not open. */
    if (frame.is_system_manager && frame.is_control_plane) {
      html += '<a class="nf-sheet-row" href="/alvoraa-admin">' + esc(__("Tenant admin")) + "</a>";
    }

    html += '<div class="nf-sheet-head-sm" id="nf-theme-head">' + esc(__("Light or dark")) + "</div>"
      + '<div class="nf-themes" role="radiogroup" aria-labelledby="nf-theme-head">'
      + themeChoice("auto", __("Match my phone"))
      + themeChoice("light", __("Light"))
      + themeChoice("dark", __("Dark"))
      + "</div>";

    /* Log out, in the same release that removes Frappe's own website bar - or
       a person has no way out of the portal at all (AC-16). */
    html += '<button type="button" class="nf-sheet-row" id="nf-logout">'
      + esc(__("Log out")) + "</button>";

    /* No language row. A language is offered only when the site has it enabled
       AND alvoraa_portal ships a translation for it; in Wave 1 that is English
       alone, so no list is computed and no control is built (AC-18, W1D-04). */

    openSheet(__("Your account"), html, function (body) {
      body.querySelectorAll('input[name="nf-theme"]').forEach(function (input) {
        input.addEventListener("change", function () { setTheme(input.value); });
      });
      var out = el("nf-logout");
      if (out) { out.onclick = logout; }
    }, opener);
  }

  function themeChoice(value, label) {
    var on = readTheme() === value ? " checked" : "";
    return '<label class="nf-theme"><input type="radio" name="nf-theme" value="'
      + esc(value) + '"' + on + "><span>" + esc(label) + "</span></label>";
  }

  function logout() {
    api("logout", {}).then(function () {
      window.location.href = "/login";
    }).catch(function () {
      window.location.href = "/?cmd=web_logout";
    });
  }

  /* ── the theme switch (AC-19) ────────────────────────────────────────────── */

  var THEME_KEY = "alvoraa-theme";

  function readTheme() {
    try { return window.localStorage.getItem(THEME_KEY) || "auto"; }
    catch (e) { return "auto"; }
  }

  function setTheme(value) {
    try { window.localStorage.setItem(THEME_KEY, value); } catch (e) { /* private window */ }
    applyTheme(value);
  }

  function applyTheme(value) {
    var root = document.documentElement;
    if (value === "auto") { root.removeAttribute("data-theme"); }
    else { root.setAttribute("data-theme", value); }
  }

  function watchSystemTheme() {
    if (!window.matchMedia) { return; }
    var query = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () {
      /* "Match my phone" has to follow a change of the phone's setting without
         a reload. The design system's dark rules are already inside a
         prefers-color-scheme block, so removing the attribute is all it takes -
         but the attribute has to be re-read, or a stale one wins. */
      if (readTheme() === "auto") { applyTheme("auto"); }
    };
    if (query.addEventListener) { query.addEventListener("change", onChange); }
    else if (query.addListener) { query.addListener(onChange); }
  }

  /* ── boot (US-2) ─────────────────────────────────────────────────────────── */

  function loadCounts(retry) {
    return api(COUNTS, {}).then(function (data) {
      counts = data;
      countsFailed = false;
      paintCounts();
      if (retry && current) { route(); }
    }).catch(function () {
      countsFailed = true;
      counts = null;
      paintCounts();
      if (retry && current) { route(); }
    });
  }

  function paintCounts() {
    var badge = el("nf-bell-badge");
    var label = el("nf-bell-label");
    var n = counts ? counts.total : 0;
    /* When the counts fail the bell shows NO number and the rest of the page
       still works (AC-32). A stale or guessed number would be worse than none. */
    badge.hidden = !(counts && n > 0);
    badge.textContent = n > 0 ? String(n) : "";
    label.textContent = countsFailed ? __("Inbox")
      : (n > 0 ? __("Inbox, {0} waiting", [n]) : __("Inbox, nothing waiting"));
    if (frame) { drawMenu(); drawBottomBar(); if (current) { markCurrent(current); } }
  }

  /* `get_frame` is the one call the page cannot do without. When it fails the
     page says what happened, offers Try again, and carries a code that holds no
     personal data (AC-33). When the SESSION has ended the person goes to the
     login page instead - being told the portal is broken when you are simply
     signed out sends you to the wrong place (AC-62). */
  function boot() {
    showState("loading", SAY.loading);
    var started = api(FRAME, {}).then(function (data) {
      frame = data;
      frame.allowedSet = {};
      frame.allowed_pages.forEach(function (page) { frame.allowedSet[page] = true; });
      frame.tenantName = document.body.getAttribute("data-tenant-name") || "";
      /* Which empty-search sentence to use. A store's HR person is an HR user
         who carries a Branch permission; the server tells us, because the
         server is what enforces it. */
      frame.scope_is_store = !!frame.scope_is_store;
      paintAvatar();
      drawMenu();
      drawBottomBar();
      el("nf-root").removeAttribute("data-nf-booting");
      route();
    }).catch(function (err) {
      if (isSignedOut(err)) {
        window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname);
        return;
      }
      showState("error", SAY.pageFailed(errorCode()), function () { window.location.reload(); });
    });
    /* Both calls go out together, and neither waits on a timer (AC-7). */
    loadCounts(false);
    return started;
  }

  /* The browser's own idea of who it is. Frappe sets this cookie on every
     response, so it is rewritten to "Guest" by the very response that refused
     the call. Reading it AFTER a failure is what makes the test below safe. */
  function userCookie() {
    var m = document.cookie.match(/(?:^|;\s*)user_id=([^;]*)/);
    if (!m) { return ""; }
    try { return decodeURIComponent(m[1]); } catch (e) { return m[1]; }
  }

  /* Has the SESSION ended, or was this person simply refused?

     Being told the portal is broken when you are only signed out sends you to
     the wrong place (AC-62) - and bouncing a signed-IN person to /login, which
     redirects them back here, which bounces them again, is worse than either.

     The status alone cannot tell the two apart. Proved in a browser on
     2026-09-24: a session that has ended is answered 403 PermissionError, not
     401, because Frappe has already turned the caller into Guest by then. What
     DOES tell them apart is the `user_id` cookie that same response sets -
     "Guest" for an ended session, the person's own address for a refusal. */
  function isSignedOut(err) {
    var type = err && err.exc_type;
    var status = err && err.status;
    if (type === "AuthenticationError" || type === "SessionExpired" || status === 401) {
      return true;
    }
    if (status !== 403) { return false; }
    var who = userCookie();
    return who === "Guest" || who === "";
  }

  function paintAvatar() {
    var me = frame.me || {};
    var node = el("nf-avatar");
    node.innerHTML = esc(initials(me.employee_name || frame.user_full_name))
      + (me.image ? '<img src="' + esc(me.image) + '" alt="" onerror="this.remove()">' : "");
  }

  /* ── wiring ──────────────────────────────────────────────────────────────── */

  function wire() {
    el("nf-menu-btn").addEventListener("click", function () {
      setRail(el("nf-menu-btn").getAttribute("aria-expanded") !== "true");
    });
    el("nf-scrim").addEventListener("click", function () { setRail(false); });
    el("nf-search-btn").addEventListener("click", function () {
      openSearch(el("nf-search-btn"));
    });
    el("nf-profile-btn").addEventListener("click", function () {
      openProfile(el("nf-profile-btn"));
    });
    el("nf-bell").addEventListener("click", function () { go("inbox"); });
    el("nf-back").addEventListener("click", function () { window.history.back(); });

    document.addEventListener("click", function (event) {
      var close = event.target.closest && event.target.closest("[data-nf-sheet-close]");
      if (close) { event.preventDefault(); closeSheet(); return; }
      var goRow = event.target.closest && event.target.closest("[data-nf-sheet-go]");
      if (goRow) { closeSheet(); }
    });

    document.addEventListener("keydown", function (event) {
      /* Escape closes the menu and any sheet, in that order of likelihood
         (AC-15). */
      if (event.key === "Escape") {
        if (sheetIsOpen()) { closeSheet(); return; }
        if (el("nf-menu-btn").getAttribute("aria-expanded") === "true") { setRail(false); }
        return;
      }
      /* Ctrl K and Cmd K open search (AC-28). */
      if ((event.ctrlKey || event.metaKey) && (event.key === "k" || event.key === "K")) {
        event.preventDefault();
        openSearch();
        return;
      }
      trapFocus(event);
    });

    window.addEventListener("hashchange", route);
    watchSystemTheme();
  }

  /* The theme is applied by a small inline script in the page HEAD, before the
     stylesheet, so the first paint is already the right colour. This is the
     later half: it keeps working when the person changes it. */
  applyTheme(readTheme());

  function start() {
    if (!el("nf-root")) { return; }
    wire();
    return boot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  /* What the tests drive. Deliberately small: the browser tests exercise the
     page through these, not through internals, so a rewrite that keeps the
     behaviour keeps the tests. */
  window.NextFrame = {
    start: start,
    boot: boot,
    route: route,
    go: go,
    toast: toast,
    openSearch: openSearch,
    openProfile: openProfile,
    closeSheet: closeSheet,
    sheetIsOpen: sheetIsOpen,
    setTheme: setTheme,
    readTheme: readTheme,
    emptySearchSentence: emptySearchSentence,
    defaultRouteFor: defaultRouteFor,
    matchingPages: matchingPages,
    /* AC-62's rule, exposed because it is the one place a refusal and an ended
       session are told apart, and getting it wrong either strands a person on
       an error page or bounces them between /login and here for ever. */
    isSignedOut: isSignedOut,
    SAY: SAY,
    MENU: MENU,
    _set: function (f, c) { frame = f; counts = c; },  /* tests only */

    /* Slice 042: how a panel file joins the page. Called at load time by
       next-home.js and next-inbox.js, which the page pulls in after this one.
       A route with no panel keeps the behaviour it had. */
    panel: function (route, draw) { panels[route] = draw; },
    hasPanel: function (route) { return !!panels[route]; }
  };
})();
