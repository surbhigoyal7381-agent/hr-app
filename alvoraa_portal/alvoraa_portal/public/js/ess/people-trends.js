/* People trends (slice 090). One call behind the page; the server decides what may be
   shown, and a figure that is not shared simply is not in the answer. Nothing is kept in
   the browser. All dynamic text goes through esc(). Prefix: pt. */
(function () {
  "use strict";
  var METHOD = "alvoraa_portal.people_trends.get_people_trends";
  var SAVE = "alvoraa_portal.people_trends.save_people_trends_period";
  var PERIODS = [7, 30, 90, 180, 365];
  var NAMES = {7: "1 week", 30: "1 month", 90: "3 months", 180: "6 months", 365: "1 year"};
  var BEFORE = {7: "the 7 days before", 30: "the 30 days before", 90: "the 3 months before",
                180: "the 6 months before", 365: "the year before"};
  var S = {period: null, filter: {}, data: null, req: 0, save: null, loading: false};

  function T(text, args) {
    var out = (typeof window.__ === "function") ? window.__(text) : text;
    (args || []).forEach(function (a, i) { out = out.split("{" + i + "}").join(a); });
    return out;
  }
  function h(s) { return window.esc ? window.esc(String(s)) : String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function day(iso, year) {
    var d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, year ? {day: "numeric", month: "short", year: "numeric"} : {day: "numeric", month: "short"});
  }
  function month(iso) { return new Date(iso + "T00:00:00").toLocaleDateString(undefined, {month: "short"}); }
  function monthYear(iso) { return new Date(iso + "T00:00:00").toLocaleDateString(undefined, {month: "short", year: "numeric"}); }
  function body() { return document.getElementById("pt-body"); }
  function live(msg) { var e = document.getElementById("pt-live"); if (e) e.textContent = msg; }
  function change(c, p, unit) {
    if (c === null || c === undefined || p === null || p === undefined) return "";
    var x = Math.round((c - p) * 10) / 10;
    if (x === 0) return T("Same as before");
    return (x > 0 ? T("Up {0}", [Math.abs(x) + (unit || "")]) : T("Down {0}", [Math.abs(x) + (unit || "")]));
  }
  var NS = '<span class="pt-ns">' + h(T("Not shared")) + "</span>";
  function tile(label, value, sub) {
    return '<div class="pt-tile"><div class="pt-l">' + h(label) + '</div><div class="pt-v">' + value + '</div><div class="pt-c">' + (sub || "") + "</div></div>";
  }
  function tableOf(rows, cols) {
    return '<div class="pt-wrap"><table><tr><th>' + h(T("Period")) + "</th>" + cols.map(function (c) { return "<th>" + h(c) + "</th>"; }).join("") + "</tr>" +
      rows.map(function (r) { return "<tr><td>" + h(r[0]) + "</td>" + r.slice(1).map(function (v) { return "<td>" + h(v) + "</td>"; }).join("") + "</tr>"; }).join("") + "</table></div>";
  }
  function axis(lo, hi) {
    var span = hi - lo || 1, raw = span / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = [1, 2, 5, 10].map(function (x) { return x * mag; }).find(function (x) { return x >= raw; });
    var t = [];
    for (var v = Math.floor(lo / step) * step; v <= hi + 1e-9; v += step) t.push(Math.round(v * 100) / 100);
    return t;
  }
  /* Plain SVG, no library. bars: [{v, c}] drawn up/down from zero; line: values. */
  function chart(labels, series, unit) {
    var w = 560, hgt = 210, ml = 38, mr = 8, mt = 10, mb = 26, pw = w - ml - mr, ph = hgt - mt - mb, n = labels.length, vals = [0];
    series.forEach(function (s) { vals = vals.concat(s.v.filter(function (v) { return v !== null; })); });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), tk = axis(lo, hi);
    lo = Math.min(lo, tk[0]); hi = Math.max(hi, tk[tk.length - 1]);
    function y(v) { return mt + ph - (v - lo) / ((hi - lo) || 1) * ph; }
    function x(i) { return ml + pw * (i + 0.5) / n; }
    var bw = Math.min(28, pw / n * 0.6), o = '<svg viewBox="0 0 ' + w + " " + hgt + '" width="100%" aria-hidden="true">';
    tk.forEach(function (t) {
      o += '<line x1="' + ml + '" x2="' + (w - mr) + '" y1="' + y(t) + '" y2="' + y(t) + '" style="stroke:var(--border)"/><text x="' + (ml - 6) + '" y="' + (y(t) + 4) + '" text-anchor="end" font-size="12" style="fill:var(--text2)">' + t + (unit || "") + "</text>";
    });
    series.forEach(function (s) {
      if (s.t === "bar") s.v.forEach(function (v, i) { var a = y(v), b = y(0); o += '<rect x="' + (x(i) - bw / 2) + '" y="' + Math.min(a, b) + '" width="' + bw + '" height="' + Math.max(1, Math.abs(a - b)) + '" rx="2" style="fill:' + s.c + '"/>'; });
      else {
        var pts = s.v.map(function (v, i) { return v === null ? null : x(i) + "," + y(v); }).filter(Boolean).join(" ");
        o += '<polyline fill="none" stroke-width="2.5" points="' + pts + '" style="stroke:' + s.c + '"/>';
      }
    });
    var every = Math.ceil(n / Math.max(2, Math.floor(pw / 64)));
    labels.forEach(function (l, i) { if (i % every === 0) o += '<text x="' + x(i) + '" y="' + (hgt - 8) + '" text-anchor="middle" font-size="12" style="fill:var(--text2)">' + h(l) + "</text>"; });
    return o + "</svg>";
  }
  function binLabels(d, points) {
    return points.map(function (p) {
      return d === 7 ? day(p.start) : (d <= 90 ? T("w/c {0}", [day(p.start)]) : month(p.start));
    });
  }

  /* ── sections ── */
  function scopeLine(d) {
    var sc = d.scope, parts = [sc.company || T("All companies")];
    ["branch", "department", "employment_type"].forEach(function (k) { if (sc[k]) parts.push(sc[k]); });
    var w = d.window;
    return '<p class="pt-sub"><b>' + h(T("Showing:")) + "</b> " + h(parts.join(", ")) + ", " + h(T(NAMES[d.period])) + "<br>" +
      h(day(w.start, true) + " " + T("to") + " " + day(w.end, true)) + (d.data_up_to ? " · " + h(T("Data up to {0}", [day(d.data_up_to, true)]))  : "") + "</p>";
  }
  function chips() {
    return '<div class="pt-chips" role="radiogroup" aria-label="' + h(T("Period")) + '">' + PERIODS.map(function (p) {
      return '<button type="button" class="pt-chip" role="radio" aria-checked="' + (p === S.period) + '" data-pt-per="' + p + '">' + h(T(NAMES[p])) + "</button>";
    }).join("") + "</div>";
  }
  function option(v, cur, label) { return '<option value="' + h(v) + '"' + (v === cur ? " selected" : "") + ">" + h(label === undefined ? v : label) + "</option>"; }
  function filters(d) {
    var f = d.filters, sc = d.scope, applied = (sc.branch ? 1 : 0) + (sc.department ? 1 : 0) + (sc.employment_type ? 1 : 0) + ((f.companies.length && sc.company) ? 1 : 0);
    function sel(name, label, list, cur, all) {
      return "<label>" + h(label) + '<select data-pt-f="' + name + '">' + option("", cur || "", all) + list.map(function (i) {
        return option(i.value, cur || "", i.value + (i.shared ? "" : " (" + T("Not shared") + ")"));
      }).join("") + "</select></label>";
    }
    var companyField = f.companies.length
      ? sel("company", T("Company"), f.companies, sc.company, T("All companies"))
      : "<label>" + h(T("Company")) + '<br><span class="pt-ns">' + h(sc.company || "") + "</span></label>";
    var open = window.innerWidth > 768 ? " open" : "";
    return "<details class=\"pt-card\"" + open + "><summary>" + h(T("Filters")) + (applied ? " · " + h(T("{0} applied", [applied])) : "") + '</summary><div class="pt-frow">' +
      companyField + sel("branch", T("Branch"), f.branches, sc.branch, T("All branches")) + sel("department", T("Department"), f.departments, sc.department, T("All departments")) +
      sel("employment_type", T("Employment type"), f.employment_types, sc.employment_type, T("All types")) + "</div>" +
      ((sc.branch || sc.department || sc.employment_type) ? '<button type="button" class="pt-link" data-pt-clear>' + h(T("Clear filters")) + "</button>" : "") + "</details>";
  }
  function banner(title, lines, buttons) {
    return '<div class="pt-banner" role="status"><h2>' + h(title) + "</h2>" + lines.map(function (l) { return "<p>" + h(l) + "</p>"; }).join("") + (buttons || "") + "</div>";
  }
  function clearButtons() {
    return '<button type="button" class="pt-link" data-pt-why>' + h(T("Why is this not shared?")) + '</button> <button type="button" class="pt-btn" data-pt-clear>' + h(T("Clear filters")) + "</button>";
  }
  function peopleCard(d) {
    var p = d.people, b = p.before, w = d.window, sub;
    if (w.compare) sub = T("Changes compare with {0} ({1} to {2}).", [T(BEFORE[d.period]), day(w.compare.start, true), day(w.compare.end, true)]);
    else sub = T("No earlier window to compare with. Records start in {0}.", [monthYear(w.records_start)]);
    if (w.clipped) sub += " " + T("This window shows {0} days, from the start of your records.", [w.days]);
    var hasLeft = p.left !== undefined;
    var o = '<section class="pt-card"><h2>' + h(T("People")) + '</h2><p class="pt-sub">' + h(sub) + '</p><div class="pt-tiles">' +
      tile(T("Headcount"), p.headcount, hasLeft ? h(p.net === 0 ? T("Same since {0}", [day(w.start)]) : (p.net > 0 ? T("Up {0} since {1}", [p.net, day(w.start)]) : T("Down {0} since {1}", [-p.net, day(w.start)]))) : "") +
      tile(T("Joined"), p.joined, b ? h(change(p.joined, b.joined)) : "") +
      tile(T("Left"), hasLeft ? p.left : NS, hasLeft && b ? h(change(p.left, b.left)) : "") +
      tile(T("Net change"), hasLeft ? (p.net > 0 ? "+" : "") + p.net : NS, hasLeft && b ? h(change(p.net, b.net)) : "") +
      tile(T("Attrition"), hasLeft && p.attrition !== null ? p.attrition + "%" : (hasLeft ? "–" : NS), hasLeft && b ? h(change(p.attrition, b.attrition, " " + T("points"))) : "") +
      "</div>" + '<p class="pt-note">' + h(T("Left means status Left and a relieving date on or before {0}. Someone serving notice is not counted yet. Attrition is people who left divided by average headcount in this window, not a yearly rate.", [day(w.end)])) + "</p>";
    if (d.data_quality) o += '<div class="pt-dq">' + h(T("{0} leavers have no relieving date. HR is asked to fix this.", [d.data_quality.no_relieving])) + "</div>";
    return o + "</section>";
  }
  function earlyCard(d) {
    var e = d.early, o = '<section class="pt-card"><h2>' + h(T("Early leavers")) + '</h2><p class="pt-sub">' + h(T("Of people who joined in this period, how many left soon after joining. Only people whose first stretch is over are counted.")) + "</p>";
    if (!e.shared) {
      var msg = e.reason === "whole_company_only" ? T("Early leavers are shown for the whole company only.") : T("Not shared: too few people in this group for a fair picture");
      return o + "<p>" + h(msg) + "</p></section>";
    }
    o += '<div class="pt-tiles">' + e.cells.map(function (c) {
      var n = T(NAMES[c.within]), v, s;
      if (!c.cohort) { v = T("Too early to tell"); s = T("Everyone who joined in this period is still inside their first {0}.", [n]); }
      else {
        v = T("{0} of {1}", [c.left, c.cohort]);
        s = T("joiners left within {0} ({1}%)", [n, Math.round(c.left / c.cohort * 100)]) + (c.inside ? ". " + T("Too early to tell for {0} more who joined in the last {1}.", [c.inside, n]) : "");
      }
      return tile(T("Within {0}", [n]), h(v), h(s));
    }).join("") + "</div>";
    return o + "</section>";
  }
  function chartCard(d) {
    var c = d.chart, o = '<section class="pt-card"><h2>' + h(T("Joined, left and running net change")) + "</h2>";
    if (!c.shared) return o + "<p>" + NS + " " + h(T("Too few people joined or left in this group to chart without pointing at someone. Try a longer period or a wider group.")) + "</p></section>";
    var labels = binLabels(d.period, c.points), j = c.points.map(function (p) { return p.joined; }), l = c.points.map(function (p) { return p.left; }), n = c.points.map(function (p) { return p.net; });
    o += '<p class="pt-sub">' + h(d.period === 7 ? T("Each day") : (d.period <= 90 ? T("Each week") : T("Each month"))) + "</p>" +
      '<div class="pt-legend"><span>' + h(T("Joined (bars up)")) + "</span><span>" + h(T("Left (bars down)")) + "</span><span>" + h(T("Running net change (line)")) + "</span></div>" +
      '<div role="img" aria-label="' + h(T("Chart of joined, left and running net change. Total joined {0}, left {1}, net {2}. A table follows.", [d.people.joined, d.people.left, d.people.net])) + '">' +
      chart(labels, [{t: "bar", v: j, c: "var(--primary)"}, {t: "bar", v: l.map(function (x) { return -x; }), c: "var(--text3)"}, {t: "line", v: n, c: "var(--text)"}]) + "</div>" +
      "<details><summary>" + h(T("Show as a table")) + "</summary>" + tableOf(labels.map(function (x, i) { return [x, j[i], l[i], n[i]]; }), [T("Joined"), T("Left"), T("Net so far")]) + "</details>";
    return o + "</section>";
  }
  function attendanceCard(d) {
    var a = d.attendance, o = '<section class="pt-card"><h2>' + h(T("Attendance")) + '</h2><p class="pt-sub">' + h(T("Absent days as a share of days people were expected to work. Weekly offs and holidays are not counted as expected.")) + "</p>";
    if (!a.shared) return o + "<p>" + NS + " " + h(T("Too few people have attendance records in this group for a fair picture. Try a longer period or a wider group.")) + "</p></section>";
    if (a.absent_pct === null) return o + "<p>" + h(T("No attendance recorded for this period")) + "</p></section>";
    var before = a.before ? a.before.absent_pct : null;
    o += '<div class="pt-tiles">' + tile(T("Absent"), a.absent_pct + "%", before === null ? "" : h(change(a.absent_pct, before, " " + T("points")))) +
      tile(T("Data up to"), d.data_up_to ? h(day(d.data_up_to)) : "–", a.left_out_days ? h(T("{0} days left out; HR is checking", [a.left_out_days])) : "") + "</div>";
    if (a.series) {
      var labels = binLabels(d.period, d.chart.points);
      o += '<div role="img" aria-label="' + h(T("Absent share of expected days by period")) + '">' + chart(labels, [{t: "line", v: a.series, c: "var(--primary)"}], "%") + "</div>" +
        "<details><summary>" + h(T("Show as a table")) + "</summary>" + tableOf(labels.map(function (x, i) { return [x, a.series[i] === null ? "–" : a.series[i]]; }), [T("Absent %")]) + "</details>";
    } else {
      o += "<p>" + NS + " " + h(T("The chart by period is not shared: too few people in this group in some periods.")) + "</p>";
    }
    return o + '<p class="pt-note">' + h(T("Days that look wrong (for example, everyone absent on one day) are left out of this rate until HR has checked them.")) + "</p></section>";
  }
  function leaveCard(d) {
    var l = d.leave, o = '<section class="pt-card"><h2>' + h(T("Leave")) + '</h2><p class="pt-sub">' + h(T("Leave days are On Leave days from attendance. A leave that starts before the period counts only its days inside it. Half days are not counted here.")) + "</p>";
    o += '<div class="pt-tiles">' + tile(T("Leave days taken"), l.days, l.before ? h(change(l.days, l.before.days)) : "") + "</div>";
    if (l.types && l.types.length) {
      var mx = Math.max.apply(null, l.types.map(function (t) { return t.days; })) || 1;
      o += "<h3 style=\"font-size:var(--fs-base);margin:12px 0 4px\">" + h(T("By leave type")) + "</h3>" + l.types.map(function (t) {
        return '<div style="display:grid;grid-template-columns:110px 1fr 70px;gap:8px;align-items:center"><span>' + h(t.type || T("Other")) + '</span><div style="background:var(--surface2);border-radius:var(--r-sm);height:10px"><div style="background:var(--primary);height:10px;border-radius:var(--r-sm);width:' + (t.days / mx * 100) + '%"></div></div><span style="text-align:right">' + h(T("{0} days", [t.days])) + "</span></div>";
      }).join("") + '<p class="pt-note">' + h(T("Small leave types are grouped under Other so no one can be picked out.")) + "</p>";
    }
    o += '<p class="pt-note">' + h(T("Waiting for approval: {0} requests (count only)", [l.pending])) + "</p>";
    if (l.series) {
      var labels = binLabels(d.period, d.chart.points);
      o += '<div role="img" aria-label="' + h(T("Leave days by period, total {0}", [l.days])) + '">' + chart(labels, [{t: "bar", v: l.series, c: "var(--primary)"}]) + "</div>" +
        "<details><summary>" + h(T("Show as a table")) + "</summary>" + tableOf(labels.map(function (x, i) { return [x, l.series[i]]; }), [T("Leave days")]) + "</details>";
    } else {
      o += "<p>" + NS + " " + h(T("The chart by period is not shared: too few people in this group in some periods.")) + "</p>";
    }
    return o + "</section>";
  }
  function companiesCard(d) {
    if (!d.by_company) return "";
    return '<section class="pt-card"><h2>' + h(T("By company")) + '</h2><p class="pt-sub">' + h(T("In alphabetical order. This is not a ranking.")) + '</p><div class="pt-cos">' + d.by_company.map(function (c) {
      if (!c.shared) return '<div class="pt-co"><b>' + h(c.company) + "</b><br>" + NS + "</div>";
      return '<div class="pt-co"><b>' + h(c.company) + "</b><br><span>" + h(T("Headcount {0}", [c.headcount])) + "</span> <span>" + h(T("Net {0}", [(c.net > 0 ? "+" : "") + c.net])) + "</span> <span>" + h(T("Left {0}", [c.left])) +
        "</span>" + (c.absent_pct === null || c.absent_pct === undefined ? "" : " <span>" + h(T("Absent {0}%", [c.absent_pct])) + "</span>") + "</div>";
    }).join("") + "</div></section>";
  }
  function howCard(d) {
    return "<details class=\"pt-card\"><summary>" + h(T("How these figures are counted")) + "</summary><p>" + h(T("Headcount is people employed on the last day. Joined and Left are inside the period. Net change is joined minus left. Absent is absent days divided by days people were expected. Leave days are On Leave days from attendance. Leaders see totals only: no names and no reasons for leave. The smallest group we show is {0} people.", [d.minimum])) + "</p></details>";
  }

  function render() {
    var d = S.data, el = body();
    if (!el || !d) return;
    el.setAttribute("aria-busy", "false");
    if (d.state === "not_set_up") {
      el.innerHTML = banner(T("People trends is not set up for you yet"), [T("You have the Leadership role, but no company or branch is linked to your account. We show nothing rather than guess."), T("Copy this message to your HR or system administrator:"), T("Please link my user to a Company so I can open People trends.")],
        '<button type="button" class="pt-btn" data-pt-copy>' + h(T("Copy message")) + "</button>");
      return;
    }
    if (d.state === "no_people") {
      el.innerHTML = banner(T("No people records in this view yet"), [T("People trends counts joiners and leavers from Employee records, then adds attendance and leave. This company has no Employee records yet, so there is nothing to count."), T("Ask your HR team to add the employee records.")]);
      return;
    }
    var head = scopeLine(d) + chips() + filters(d);
    if (d.state === "no_match") { el.innerHTML = head + banner(T("No one matches these filters"), [T("This company has no people with that mix of branch, department and employment type.")], '<button type="button" class="pt-btn" data-pt-clear>' + h(T("Clear filters")) + "</button>"); return; }
    if (d.state === "not_shared") {
      var few = d.reason === "few";
      el.innerHTML = head + banner(T("Not shared"), [few ? T("Not shared: too few people in this group for a fair picture") : T("Not shared: it would let someone work out a smaller group's figures"),
        few ? T("Try a wider group, such as the whole company.") : T("Another group is too small to share, and showing this one would reveal it by subtraction. Try a wider group, such as the whole company.")], clearButtons());
      return;
    }
    el.innerHTML = head + '<section class="pt-card" aria-label="' + h(T("Summary")) + '"><p>' + h(d.headline) + "</p></section>" + peopleCard(d) + earlyCard(d) + chartCard(d) + attendanceCard(d) + leaveCard(d) + companiesCard(d) + howCard(d);
  }

  /* ── talking to the server ──
     A plain fetch to /api/method/ (OPS-18): the website frappe.call posts to "/" with a
     `cmd`, which skips the path gates, and never reports a refusal. Real HTTP status codes
     tell a refusal (403, PT-SCOPE) from a failure (anything else, PT-LOAD). */
  function post(method, args) {
    var headers = {"Content-Type": "application/json"};
    var tok = (window.frappe && frappe.csrf_token) || "";
    if (tok && tok !== "None") headers["X-Frappe-CSRF-Token"] = tok;
    return fetch("/api/method/" + method, {method: "POST", credentials: "same-origin", headers: headers, body: JSON.stringify(args)})
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) { return {status: res.status, ok: res.ok, data: data}; });
      });
  }
  function params() {
    var a = {};
    if (S.period) a.period = S.period;
    Object.keys(S.filter).forEach(function (k) { if (S.filter[k]) a[k] = S.filter[k]; });
    return a;
  }
  function fetchNow(previous) {
    var mine = ++S.req, timer;
    if (!S.data) body().innerHTML = '<div class="pt-sk"></div><div class="pt-sk"></div><div class="pt-sk" style="height:200px"></div><p class="pt-note">' + h(T("Loading People trends. The period bar stays usable; figures fill in as they arrive.")) + "</p>";
    function fail(refused) {
      if (mine !== S.req) return;
      clearTimeout(timer);
      if (S.data && !refused) {
        var note = '<p class="pt-note" role="alert">' + h(T("The new figures did not load. These figures are still for {0}.", [T(NAMES[S.data.period])])) + ' <button type="button" class="pt-link" data-pt-retry>' + h(T("Try again")) + "</button></p>";
        body().insertAdjacentHTML("afterbegin", note);
        return;
      }
      body().setAttribute("aria-busy", "false");
      body().innerHTML = refused
        ? banner(T("That view is not available to you"), [T("Choose from the lists on this page. If you think this is wrong, tell HR and quote Code PT-SCOPE.")], '<button type="button" class="pt-btn" data-pt-clear>' + h(T("Clear filters")) + "</button>")
        : banner(T("We could not load People trends"), [T("Your data is safe. The page did not get an answer from the server in time."), T("Try again. If it keeps happening, tell HR and quote Code PT-LOAD.")], '<button type="button" class="pt-btn" data-pt-retry>' + h(T("Try again")) + "</button>");
    }
    if (navigator.onLine === false) { setTimeout(function () { fail(false); }, 0); return; }
    timer = setTimeout(function () { fail(false); }, 15000);
    post(METHOD, params()).then(function (r) {
      if (mine !== S.req) return;                 /* the answer to the last tap wins */
      clearTimeout(timer);
      if (r.status === 403) { fail(true); return; }
      if (!r.ok || !r.data || !r.data.message) { fail(false); return; }
      S.data = r.data.message; S.period = S.data.period;
      render();
      live(T("Showing {0}. All figures updated.", [T(NAMES[S.period] || "")]));
      var chip = body().querySelector('[data-pt-per="' + S.period + '"]');
      if (previous && chip) chip.focus();
    }, function () { fail(false); });
  }
  function savePeriod() {
    clearTimeout(S.save);
    S.save = setTimeout(function () {
      post(SAVE, {period: S.period}).then(null, function () {});
    }, 2000);
  }
  function sheet() {
    var few = '<p><b>' + h(T("Not shared: too few people in this group for a fair picture.")) + "</b></p>";
    var scrim = document.createElement("div"), box = document.createElement("div"), last = document.activeElement;
    scrim.id = "pt-sheet-scrim"; box.id = "pt-sheet";
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-label", T("Why is this not shared?"));
    var min = S.data ? S.data.minimum : 5;
    box.innerHTML = "<h2>" + h(T("Why is this not shared?")) + "</h2>" + few +
      "<p>" + h(T("With a small group, a total can point at one person, and that person is a colleague. So we only show figures for {0} or more people.", [min])) + "</p>" +
      "<p>" + h(T("Sometimes a larger group is not shared either. That is when showing it would let someone work out a smaller group by subtraction.")) + "</p>" +
      "<p>" + h(T("A group that has had fewer than {0} people at any time in the last two years stays hidden.", [min])) + "</p>" +
      "<p>" + h(T("Leaders see totals only. Names and reasons for leave are never shown here.")) + '</p><button type="button" class="pt-btn" id="pt-sheet-x">' + h(T("Close")) + "</button>";
    function close() { scrim.remove(); box.remove(); document.removeEventListener("keydown", key); if (last && last.focus) last.focus(); }
    function key(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", key);
    scrim.onclick = close;
    document.body.appendChild(scrim); document.body.appendChild(box);
    var x = box.querySelector("#pt-sheet-x"); x.onclick = close; x.focus();
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("[data-pt-per],[data-pt-clear],[data-pt-retry],[data-pt-why],[data-pt-copy]") : null;
    if (!t || !body() || !body().contains(t)) return;
    if (t.hasAttribute("data-pt-per")) { S.period = parseInt(t.getAttribute("data-pt-per"), 10); savePeriod(); fetchNow(true); }
    else if (t.hasAttribute("data-pt-clear")) { S.filter = {}; fetchNow(false); }
    else if (t.hasAttribute("data-pt-retry")) { fetchNow(false); }
    else if (t.hasAttribute("data-pt-why")) { sheet(); }
    else if (t.hasAttribute("data-pt-copy")) {
      if (navigator.clipboard) navigator.clipboard.writeText(T("Please link my user to a Company so I can open People trends."));
      t.textContent = T("Copied");
    }
  });
  document.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || !t.getAttribute || !t.getAttribute("data-pt-f") || !body() || !body().contains(t)) return;
    var k = t.getAttribute("data-pt-f");
    if (k === "company") S.filter = {company: t.value};
    else S.filter = {company: S.filter.company || (S.data && S.data.scope.company) || "", [k]: t.value};
    fetchNow(false);
  });

  window.ptLoad = function () { S.data = null; S.filter = {}; fetchNow(false); };
})();
