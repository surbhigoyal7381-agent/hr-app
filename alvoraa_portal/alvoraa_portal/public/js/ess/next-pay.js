/* Slice 043, Wave 3: the Pay panel, and the Why? sheet behind a deduction.
 *
 * What this file may do: ask `pay_api.get_pay` and `pay_api.
 * get_deduction_explanation`, and draw the answers.
 * What it may not do: decide anything, and above all COMPUTE anything. Not a
 * total, not a year figure, not a difference between two months. Every number
 * on this screen was worked out by payroll and stored; this draws it.
 *
 * **The Why? sheet is the sensitive one.** Its payload and its wording are
 * built and tested on the server (`pay_api._explanation`, `test_why_sheet_043`),
 * and this file RENDERS THEM AS THEY ARE. It does not rephrase a sentence, does
 * not shorten one, and does not add one. Three things have to stay true on the
 * screen and they are true because the server said them:
 *
 *   it says the decision was automatic, when it was made and under which rule;
 *   the remedy it states is the remedy that exists - correcting a day does NOT
 *     undo a deduction already applied;
 *   showing it creates no record about the person: no read receipt, no
 *     "acknowledged" flag, nothing inferred from closing the sheet (AC-61).
 *
 * The last one is why closing this sheet calls nothing.
 *
 * **Payroll rounding is untouched, and this screen must not hide it.** 555 of
 * 800 PP Jewellers slips print a net the bank does not pay. That is an open
 * decision. So the hero shows the ROUNDED total - the figure actually paid,
 * which a person can check against their bank - and the exact net is shown
 * below it rather than instead of it. A screen that showed only one of them
 * would make whichever it chose look authoritative.
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-pay";
  var PAY = "alvoraa_portal.pay_api.get_pay";
  var WHY = "alvoraa_portal.pay_api.get_deduction_explanation";
  var SLIP = "alvoraa_portal.hr_api.get_payslip";

  function skeleton(on) {
    var node = document.getElementById(SKELETON);
    if (node) { node.hidden = !on; }
  }

  function words(ctx) {
    var __ = ctx.__;
    return {
      takeHome: __("Take-home"),
      exactNet: __("Exact amount on the payslip"),
      period: __("Period"),
      paidDays: __("Days paid"),
      download: __("Download PDF"),
      earnings: __("What you earned"),
      deductions: __("What was taken off"),
      yearSoFar: __("This financial year so far"),
      gross: __("Before deductions"),
      slips: __("Your payslips"),
      why: __("Why?"),
      whyTitle: __("Why this was taken off"),
      noPayslips: __("No payslips have been issued to you yet."),
      cardFailed: __("This could not load."),
      handEntered: __("This was entered by hand, so there are no days behind it."),
      week: __("The week this covers"),
      counted: __("Counted"),
      free: __("Free"),
      howDecided: __("How this was decided"),
      whatToDo: __("If you think this is wrong"),
      /* Whole phrases with placeholders - never a sentence built by joining
         pieces, because the figures move in word order between English, Hindi
         and Punjabi (AC-40). */
      upTo: function (d) { return __("Up to {0}", [d]); },
      readOff: function (s) { return __("Read from payslip {0}", [s]); },
      daysCame: function (t, d) { return __("{0}: {1} days", [t, d]); },
      minutesLate: function (n) { return __("{0} min", [n]); },
      roundedUp: function (a, b) {
        return __("{0} days, rounded up to {1}", [a, b]);
      }
    };
  }

  /* ── the screen ──────────────────────────────────────────────────────────── */

  function draw(ctx) {
    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);
    return ctx.api(PAY, {}).then(function (data) {
      skeleton(false);
      ctx.showScreen(build(data, ctx));
      wire(data, ctx);
    }).catch(function (reason) {
      skeleton(false);
      /* AC-37. On a tenant without payroll the endpoint refuses, and the
         refusal is a SENTENCE. It is also byte-identical to the one a missing
         slip gives, which is the point: a refusal that varies tells a caller
         what the tenant bought. */
      var said = refusalSentence(reason);
      if (said) {
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + ctx.esc(said) + "</p></section>");
      }
      ctx.showState("page-error", ctx.SAY.pageFailed(ctx.errorCode()),
                    function () { draw(ctx); });
    });
  }

  /* The sentence the SERVER wrote, where it wrote one.

     The frame's `api` has already done the unwrapping: `apiError` pulls
     `_server_messages` apart and puts the sentence on `err.message`, keeping
     `exc_type` and `status` beside it. The first version of this function
     re-parsed `_server_messages` off the rejection - which is never there,
     because the frame consumed it - so every refusal fell through to the page
     error and a person who opened a month they may not see was told the page
     had broken. `next_time_pay_test.js` caught it three times over.

     The type is checked as well as the message, because when there is no
     sentence `apiError` falls back to the status text: "Forbidden" is not
     something to show anybody. */
  function refusalSentence(err) {
    if (!err || !err.message) { return ""; }
    var worded = err.exc_type === "PermissionError"
      || err.exc_type === "ValidationError"
      || err.exc_type === "DoesNotExistError";
    return worded ? err.message : "";
  }

  function build(data, ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    if (!data || !data.payslips || !data.payslips.length) {
      /* AC-39. The sentence, and nothing that looks like a broken page.
         Expenses stays reachable from the menu - this panel owns the salary
         part of Pay and nothing else. */
      return '<section class="nf-screen nf-pay"><p class="nf-screen-note">'
        + esc((data && data.note) || SAY.noPayslips) + "</p></section>";
    }
    return '<section class="nf-screen nf-pay">'
      + hero(data, esc, SAY)
      + lines(data.latest, esc, SAY)
      + yearToDate(data, esc, SAY)
      + slipList(data, esc, SAY)
      + "</section>";
  }

  function hero(data, esc, SAY) {
    var slip = data.latest || {};
    /* The rounded total, per §20 D-2 - what the bank actually paid. The exact
       net is right underneath, never replaced by it. See the file header. */
    var html = '<p class="nf-card-note">' + esc(SAY.takeHome) + "</p>"
      + '<p class="nf-pay-big">' + esc(money(data.take_home, data.currency))
      + "</p>";
    if (slip.net_pay !== slip.rounded_total) {
      html += '<p class="nf-card-note">' + esc(SAY.exactNet) + ": "
        + esc(money(slip.net_pay, data.currency)) + "</p>";
    }
    html += '<p class="nf-card-note">' + esc(slip.start_date || "") + " – "
      + esc(slip.end_date || "") + "</p>";
    if (slip.payment_days) {
      html += '<p class="nf-card-note">' + esc(SAY.paidDays) + ": "
        + esc(num(slip.payment_days)) + "</p>";
    }
    html += '<button type="button" class="nf-btn nf-btn-big" id="nf-pay-pdf"'
      + ' data-slip="' + esc(slip.name || "") + '">' + esc(SAY.download)
      + "</button>";
    return '<section class="nf-card nf-hero">' + html + "</section>";
  }

  function lines(slip, esc, SAY) {
    if (!slip) { return ""; }
    return lineCard(SAY.earnings, slip.earnings, slip.currency, esc, SAY, false)
      + lineCard(SAY.deductions, slip.deductions, slip.currency, esc, SAY, true);
  }

  function lineCard(title, rows, currency, esc, SAY, withWhy) {
    if (!rows || !rows.length) { return ""; }
    var html = '<ul class="nf-rows">';
    rows.forEach(function (row) {
      /* The Why? control appears on a line that CARRIES the link, and on no
         other. The server puts `additional_salary` on a line only where
         Frappe HR set one, so "is there something to explain" is a question
         about the payload, not a guess from the component's name. A "Late
         Coming Deduction" typed in by hand has no link and gets no control -
         and if somebody opens one anyway, AC-29's sentence says so. */
      var why = (withWhy && row.additional_salary)
        ? '<span class="nf-row-acts"><button type="button"'
          + ' class="nf-btn nf-btn-small" data-why="' + esc(row.additional_salary)
          + '">' + esc(SAY.why) + "</button></span>"
        : "";
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(row.component) + "</span></span>"
        + '<span class="nf-row-val">' + esc(money(row.amount, currency))
        + "</span>" + why + "</li>";
    });
    return card(esc(title), html + "</ul>", esc);
  }

  function yearToDate(data, esc, SAY) {
    var ytd = data.year_to_date;
    if (!ytd) { return ""; }
    /* AC-25. This figure is READ off the newest slip, by the server. Nothing
       here adds slips up - and it must not, because the list above is capped
       at twelve and a mid-year joiner's first slip is not April's. */
    var html = '<p class="nf-pay-big">' + esc(money(ytd.net, data.currency)) + "</p>"
      + '<p class="nf-card-note">' + esc(SAY.gross) + ": "
      + esc(money(ytd.gross, data.currency)) + "</p>"
      + '<p class="nf-card-note">' + esc(SAY.upTo(ytd.up_to)) + "</p>"
      + '<p class="nf-card-note">' + esc(SAY.readOff(ytd.from_slip)) + "</p>";
    return card(esc(SAY.yearSoFar), html, esc);
  }

  function slipList(data, esc, SAY) {
    var html = '<ul class="nf-rows">';
    data.payslips.forEach(function (slip) {
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(slip.start_date) + " – "
        + esc(slip.end_date) + "</span></span>"
        + '<span class="nf-row-val">'
        + esc(money(slip.rounded_total, slip.currency)) + "</span>"
        + '<span class="nf-row-acts"><button type="button"'
        + ' class="nf-btn nf-btn-small" data-slip="' + esc(slip.name) + '">'
        + esc(SAY.download) + "</button></span></li>";
    });
    return card(esc(SAY.slips), html + "</ul>", esc);
  }

  /* ── the Why? sheet ──────────────────────────────────────────────────────── */

  function openWhy(link, ctx, opener) {
    var esc = ctx.esc, SAY = words(ctx);
    ctx.api(WHY, { additional_salary: link }).then(function (why) {
      if (why && why.hand_entered) {
        /* AC-29. The sentence, and NO WEEK. An empty week would read as "the
           system thinks you were late on no days and took your money
           anyway", which is worse than saying nothing. */
        return ctx.openSheet(SAY.whyTitle,
          '<p class="nf-sheet-lead">' + esc(SAY.handEntered) + "</p>", null, opener);
      }
      ctx.openSheet(SAY.whyTitle, whyBody(why, esc, SAY), null, opener);
    }).catch(function (reason) {
      ctx.toast(refusalSentence(reason) || SAY.cardFailed, "bad");
    });
  }

  function whyBody(why, esc, SAY) {
    /* EVERY sentence below is the server's, rendered as it is. Nothing here
       rewrites one, shortens one or adds one - see the file header. The three
       that carry the most weight are `what_a_correction_does_not_do`,
       `getting_it_put_back` and `who_to_go_to`, and a static check keeps the
       false version of the first one out of the build. */
    var html = '<p class="nf-sheet-lead">' + esc(why.how_it_was_decided) + "</p>";

    html += '<h3 class="nf-card-title">' + esc(SAY.week) + "</h3>"
      + '<p class="nf-card-note">' + esc(why.week_start) + " – "
      + esc(why.week_end) + "</p>";

    html += '<ul class="nf-rows">';
    (why.violations || []).forEach(function (row) {
      /* Which ones were free is the server's `counted` flag, not a position in
         the list - a person who is told "the first one is free" and then
         counts down the list themselves must land on the same answer. */
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(row.attendance_date) + " · "
        + esc(row.violation_type || "") + "</span>"
        + '<span class="nf-row-sub">' + esc(row.actual_time || "") + " · "
        + esc(SAY.minutesLate(row.minutes)) + "</span></span>"
        + '<span class="nf-row-val">'
        + esc(row.counted ? SAY.counted : SAY.free) + "</span></li>";
    });
    html += "</ul>";

    if (why.rounded_up) {
      html += '<p class="nf-card-note">'
        + esc(SAY.roundedUp(num(why.computed_days), num(why.deduction_days)))
        + "</p>";
    }
    (why.taken_from_leave || []).forEach(function (row) {
      html += '<p class="nf-card-note">'
        + esc(SAY.daysCame(row.leave_type, num(row.days))) + "</p>";
    });

    html += '<h3 class="nf-card-title">' + esc(SAY.whatToDo) + "</h3>"
      + '<p class="nf-card-note">' + esc(why.if_a_day_is_wrong) + "</p>"
      /* The sentence this slice exists to get right. It is emphasised because
         it is the one a person most needs to have read, and it is STRONG
         rather than coloured - colour is never the only signal. */
      + '<p class="nf-sheet-strong">' + esc(why.what_a_correction_does_not_do)
      + "</p>"
      + '<p class="nf-card-note">' + esc(why.getting_it_put_back) + "</p>"
      + '<p class="nf-card-note">' + esc(why.who_to_go_to) + "</p>";
    return html;
  }

  /* ── shared bits ─────────────────────────────────────────────────────────── */

  function card(title, bodyHtml, esc) {
    return '<section class="nf-card"><h2 class="nf-card-title">' + title + "</h2>"
      + bodyHtml + "</section>";
  }

  function num(v) {
    if (v === null || v === undefined || v === "") { return "0"; }
    return String(Math.round(Number(v) * 100) / 100);
  }

  /* The slip's OWN currency, never an assumed one, and formatted by the
     browser's locale data rather than by a symbol written into this file
     (§16). A tenant paying in a currency this file had never heard of would
     otherwise get the wrong symbol on their own payslip. */
  function money(value, currency) {
    if (value === null || value === undefined || value === "") { return ""; }
    try {
      return new Intl.NumberFormat(document.documentElement.lang || undefined, {
        style: "currency", currency: currency || "INR"
      }).format(Number(value));
    } catch (e) {
      return num(value);
    }
  }

  function wire(data, ctx) {
    var root = document.getElementById("nf-screens") || document;

    Array.prototype.forEach.call(root.querySelectorAll("[data-why]"), function (node) {
      node.addEventListener("click", function () {
        openWhy(node.getAttribute("data-why"), ctx, node);
      });
    });

    Array.prototype.forEach.call(root.querySelectorAll("[data-slip]"), function (node) {
      node.addEventListener("click", function () {
        download(node.getAttribute("data-slip"), ctx);
      });
    });
  }

  /* The PDF is fetched through the same whitelisted endpoint, which checks
     ownership again on the server. It is a plain navigation rather than an
     XHR, so the phone's own viewer opens it and the download survives - and
     `download_payslip` deliberately does not touch the session, so pressing
     this cannot sign somebody out. */
  function download(name, ctx) {
    if (!name) { return; }
    window.location.href = "/api/method/" + SLIP.replace("get_payslip",
      "download_payslip") + "?name=" + encodeURIComponent(name);
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("pay", draw);
  }
  window.NextPay = {
    draw: draw,
    build: build,
    whyBody: whyBody,
    money: money
  };
})();
