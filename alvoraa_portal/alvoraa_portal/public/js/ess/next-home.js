/* Slice 042, Wave 2: the Home panel.
 *
 * Its own file, not a block inside next-frame.js. OPS-31 landed in Wave 1, so a
 * markup part costs no template cache slot and a static script costs one more
 * `<script src>` - which means Home, Inbox, Time and Pay can each have their
 * own file and two sessions building two panels never meet in one.
 *
 * What this file may do: ask `home_api.get_home`, and draw the answer.
 * What it may not do: decide anything. Every permission, every scope and every
 * number is the server's. If a card is missing from the payload it is missing
 * from the screen, and that is the whole mechanism.
 *
 * Three rules it keeps:
 *
 *   **Nothing from the server reaches innerHTML unescaped** (042 AC-60).
 *   Everything goes through the frame's `esc`, which is handed in. A
 *   Designation of `<img src=x onerror=alert(1)>` appears as text and creates
 *   no element. `next_panels_test.js` drives exactly that string.
 *
 *   **No number of its own** (042 AC-38). Home never counts anything. The bell
 *   and the Inbox menu entry are the one number, and they come from
 *   `get_nav_counts`. The "Needs you" heading carries no number at all (D-1).
 *
 *   **A card that failed says so, and the rest of the page works** (AC-32).
 *   The server marks a broken card `{error: true}`; this draws "This could not
 *   load." in that card and nothing else changes.
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-home";

  var HOME = "alvoraa_portal.home_api.get_home";


  /* The skeleton is server-rendered markup sitting in `#nf-main` (AC-31). It is
     shown while the call is in the air and hidden the moment anything real is
     on screen. It is `aria-hidden`, so the state box above it is what actually
     announces "Loading…" - two voices saying the same thing is worse than one. */
  function skeleton(on) {
    var node = document.getElementById(SKELETON);
    if (node) { node.hidden = !on; }
  }

  function draw(ctx) {
    var esc = ctx.esc, __ = ctx.__;

    var SAY = {
      needsYou: __("Needs you"),
      allClear: __("All clear."),
      cardFailed: __("This could not load."),
      tryAgain: __("Try again"),
      leaveLeft: __("Leave left"),
      comingUp: __("Coming up"),
      team: __("Your team today"),
      peers: __("Who is in today"),
      /* The sentence is ON THE CARD, not in a tooltip. It is the one place a
         person is told what this card will never say about a colleague. */
      presenceNote: __("Who is in, and who is still to come. Nothing about why anyone is away."),
      smallGroup: __("This team is too small to show numbers without saying something about one person."),
      inWord: __("In"),
      awayWord: __("Away"),
      dueWord: __("Still to come"),
      goals: __("Your goals"),
      fix: __("Fix"),
      checkIn: __("Check in"),
      checkOut: __("Check out")
    };

    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);

    return ctx.api(HOME, {}).then(function (home) {
      skeleton(false);
      if (!home || !home.me) {
        /* 042 AC-37. One plain line, no cards, no errors. */
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + esc(ctx.SAY.noEmployee) + "</p></section>");
      }
      ctx.showScreen(build(home, esc, __, SAY));
      wire(home, ctx);
    }).catch(function () {
      skeleton(false);
      ctx.showState("page-error", ctx.SAY.pageFailed(ctx.errorCode()),
                    function () { draw(ctx); });
    });
  }

  /* ── the pieces ──────────────────────────────────────────────────────────── */

  function failed(esc, SAY) {
    return '<p class="nf-card-note">' + esc(SAY.cardFailed) + "</p>";
  }

  function isError(value) {
    return !!(value && typeof value === "object" && value.error);
  }

  function hero(home, esc, SAY) {
    var today = home.today || {};
    /* 009 design decision 6: no shift, NO HERO. Not an empty hero, and not a
       hero with blank times - a check-in button for somebody who is not
       rostered today is an invitation to a refusal. */
    if (isError(today) || !today.shift) { return ""; }
    var shift = today.shift;
    var checkin = today.checkin;
    var inNow = !!(checkin && checkin.type === "IN");
    var line = inNow && checkin.time
      ? esc(SAY.checkedInAt || "") + esc(checkin.time)
      : "";
    return '<section class="nf-card nf-hero" id="nf-home-hero">'
      + '<p class="nf-hero-shift">' + esc(shift.start || "") + " – " + esc(shift.end || "") + "</p>"
      + (line ? '<p class="nf-hero-line" id="nf-home-checkin">' + line + "</p>" : "")
      + '<button type="button" class="nf-btn nf-btn-big" id="nf-home-checkin-btn"'
      + ' data-action="' + (inNow ? "OUT" : "IN") + '">'
      + esc(inNow ? SAY.checkOut : SAY.checkIn) + "</button>"
      + "</section>";
  }

  function needs(home, esc, __, SAY) {
    var rows = home.needs;
    if (isError(rows)) {
      return card(esc(SAY.needsYou), failed(esc, SAY), esc);
    }
    if (!rows || !rows.length) {
      return card(esc(SAY.needsYou),
                  '<p class="nf-card-note">' + esc(SAY.allClear) + "</p>", esc);
    }
    var body = '<ul class="nf-needs">';
    rows.forEach(function (item) {
      var extra = "";
      if (item.kind === "attendance_gap" && item.detail) {
        if (item.detail.capped) {
          extra = '<span class="nf-need-sub">'
            + esc(__("Showing the first {0} of {1}.",
                     [item.detail.days.length, item.detail.total])) + "</span>";
        }
        extra += '<button type="button" class="nf-btn nf-btn-small nf-fix"'
          + ' data-from="' + esc(item.detail.from_date) + '"'
          + ' data-to="' + esc(item.detail.to_date) + '">' + esc(SAY.fix) + "</button>";
      }
      body += '<li class="nf-need"><span class="nf-need-title">' + esc(item.title)
        + "</span>" + extra + "</li>";
    });
    body += "</ul>";
    /* D-1: the heading carries NO number. The bell and the Inbox entry are the
       one number in the product, and a second one beside it that counts
       something slightly different is the exact fault this slice exists to
       remove. */
    return card(esc(SAY.needsYou), body, esc);
  }

  function leave(home, esc, SAY) {
    if (isError(home.leave)) { return card(esc(SAY.leaveLeft), failed(esc, SAY), esc); }
    if (!home.leave || !home.leave.length) { return ""; }
    var body = '<ul class="nf-rows">';
    home.leave.forEach(function (row) {
      /* A fully used type is SHOWN, not hidden (042 AC-6). "0 of 8" is a fact
         somebody needs; a missing row reads as "you never had any". */
      body += '<li class="nf-row"><span>' + esc(row.leave_type) + "</span>"
        + '<span class="nf-row-val">' + esc(num(row.left)) + " "
        + esc(ofWord(esc, row)) + "</span></li>";
    });
    body += "</ul>";
    return card(esc(SAY.leaveLeft), body, esc);
  }

  function ofWord(esc, row) {
    return row.total === null || row.total === undefined ? "" : ("of " + num(row.total));
  }

  function num(v) {
    if (v === null || v === undefined || v === "") { return "0"; }
    return String(Math.round(Number(v) * 10) / 10);
  }

  function holidays(home, esc, SAY) {
    if (isError(home.holidays)) { return card(esc(SAY.comingUp), failed(esc, SAY), esc); }
    if (home.holiday_note) {
      return card(esc(SAY.comingUp),
                  '<p class="nf-card-note">' + esc(home.holiday_note) + "</p>", esc);
    }
    if (!home.holidays || !home.holidays.length) { return ""; }
    var body = '<ul class="nf-rows">';
    home.holidays.slice(0, 6).forEach(function (row) {
      body += '<li class="nf-row"><span>' + esc(row.date) + "</span>"
        + "<span>" + esc(row.description || "") + "</span></li>";
    });
    body += "</ul>";
    return card(esc(SAY.comingUp), body, esc);
  }

  function team(home, esc, SAY) {
    var card_ = home.team_today;
    if (isError(card_)) { return card(esc(SAY.team), failed(esc, SAY), esc); }
    /* AC-33 and AC-55: nothing to describe means the card is NOT DRAWN, rather
       than an empty frame or a silent zero. */
    if (!card_ || card_.basis === "none") { return ""; }
    var title = card_.basis === "peers" ? SAY.peers : SAY.team;
    var body = "";
    if (card_.suppressed && card_.in === null && card_.away === null && card_.due === null) {
      body = '<p class="nf-card-note">' + esc(SAY.smallGroup) + "</p>";
    } else {
      body = '<ul class="nf-counts">'
        + countRow(esc, SAY.inWord, card_.in)
        + countRow(esc, SAY.awayWord, card_.away)
        + countRow(esc, SAY.dueWord, card_.due)
        + "</ul>";
    }
    /* Colour is never the only signal - each count says its state in words. */
    body += '<p class="nf-card-note">' + esc(SAY.presenceNote) + "</p>";
    return card(esc(title), body, esc);
  }

  function countRow(esc, word, value) {
    if (value === null || value === undefined) { return ""; }
    return '<li class="nf-count"><span class="nf-count-n">' + esc(String(value))
      + '</span><span class="nf-count-w">' + esc(word) + "</span></li>";
  }

  function goals(home, esc, SAY) {
    var g = home.goals;
    if (isError(g)) { return card(esc(SAY.goals), failed(esc, SAY), esc); }
    if (!g || !g.mine || !g.mine.count) { return ""; }
    var body = '<ul class="nf-rows">';
    g.mine.rows.slice(0, 5).forEach(function (row) {
      body += '<li class="nf-row"><span>' + esc(row.goal_name || "") + "</span>"
        + '<span class="nf-row-val">' + esc(num(row.progress)) + "%</span></li>";
    });
    body += "</ul>";
    return card(esc(SAY.goals), body, esc);
  }

  function card(title, body, esc) {
    return '<section class="nf-card"><h2 class="nf-card-title">' + title + "</h2>"
      + body + "</section>";
  }

  function build(home, esc, __, SAY) {
    return '<section class="nf-screen nf-home">'
      + hero(home, esc, SAY)
      + needs(home, esc, __, SAY)
      + leave(home, esc, SAY)
      + holidays(home, esc, SAY)
      + team(home, esc, SAY)
      + goals(home, esc, SAY)
      + "</section>";
  }

  /* ── what a person can press ─────────────────────────────────────────────── */

  function wire(home, ctx) {
    var btn = document.getElementById("nf-home-checkin-btn");
    if (btn) {
      btn.addEventListener("click", function () {
        btn.disabled = true;
        /* The refusal wording for a duplicate press and for a missing position
           is `field_checkin`'s, reused. A second sentence saying the same thing
           differently is how two screens come to disagree about one rule. */
        ctx.api("alvoraa_portal.hr_api.do_checkin",
                { log_type: btn.getAttribute("data-action") })
          .then(function () { draw(ctx); })
          .catch(function (r) {
            btn.disabled = false;
            ctx.toast((r && r._server_messages) ? stripped(r) : ctx.SAY.countsFailed, "bad");
          });
      });
    }
    Array.prototype.forEach.call(document.querySelectorAll(".nf-fix"), function (node) {
      node.addEventListener("click", function () {
        /* The Fix sheet is the correction form, pre-filled with the days the
           gap rule found - the SAME days the number counted (042 AC-21). */
        ctx.go("time/fix?from=" + encodeURIComponent(node.getAttribute("data-from"))
               + "&to=" + encodeURIComponent(node.getAttribute("data-to")));
      });
    });
  }

  function stripped(r) {
    try {
      var msgs = JSON.parse(r._server_messages);
      return JSON.parse(msgs[0]).message;
    } catch (e) { return ""; }
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("home", draw);
  }
  window.NextHome = { draw: draw, build: build };
})();
