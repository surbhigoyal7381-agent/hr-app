/* Slice 042, Wave 2: the Inbox panel.
 *
 * One honest queue. Every number and every row comes from
 * `inbox_api.get_inbox`, which builds both from one filter expression per part
 * - so a count on this screen can never describe a different set from the list
 * under it.
 *
 * Three rules it keeps, and each has a check:
 *
 *   **The browser never works out a number** (042 AC-13). After a decision the
 *   row is removed and the counts are RE-READ from the server through
 *   `ctx.reloadCounts()`. Decrementing a stored number is quick, and it is how
 *   a badge starts telling a different story from the screen.
 *
 *   **A row that is drawn is a row that can be acted on** (042 AC-17). The list
 *   and the action share one scope function on the server, so Approve never
 *   returns a refusal. Where a part decides on its own screen rather than here,
 *   the card title is a link to that screen, so no row is drawn with nothing a
 *   person can do with it (review F6).
 *
 *   **A refusal is described in the server's words, never guessed** (review F5).
 *   When somebody else decided first the server says "This one has already been
 *   decided." and that sentence is shown. When the server said nothing at all -
 *   a timeout, a dropped connection - the person is told THAT, and the screen is
 *   redrawn from the server either way. This file used to say "already decided"
 *   for every failure, which told a manager on a factory-floor phone that a
 *   timed-out leave request had been handled. It had not.
 *
 *   **Nothing from the server reaches innerHTML unescaped** (042 AC-60).
 *
 * Wave 2 does NOT change who may decide an attendance correction (D-2). The
 * decide buttons call the actions that exist today, unchanged.
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-inbox";

  var INBOX = "alvoraa_portal.inbox_api.get_inbox";

  /* Each part's decide action, and what its two buttons mean. A part with no
     entry here is a list with no buttons - which is right for policies and for
     goal updates and shift changes, whose own screens do the deciding. Those
     parts get a LINK to their screen instead (042 review F6), so a row is never
     drawn with nothing a person can do with it. */
  var ACTIONS = {
    /* **The key names here are the server's parameter names, not ours.** Frappe
       keeps only the arguments the function declares (`get_newargs`) and drops
       the rest without a word, so a near-miss on a name is silent on the wire
       and a `TypeError` in the worker. This entry sent `name` where the server
       says `leave_id`, and every Approve and Decline on this screen failed from
       Wave 2 until 2026-09-25. `test_browser_call_args_045.py` now checks the
       names a browser sends against the names the server declares.

       `note` is NOT sent: `action_leave` has no parameter for it, so it was
       being dropped too. The decline reason a manager types is still not
       recorded anywhere - see the addendum to 00-impact-analysis.md, D5. */
    leave_approvals: {
      approve: "alvoraa_portal.hr_api.action_leave",
      args: function (row, yes, note) {  // eslint-disable-line no-unused-vars
        return { leave_id: row.name, action: yes ? "approve" : "reject" };
      }
    },
    attendance_fixes: {
      approve: "alvoraa_portal.attendance_correction.decide",
      args: function (row, yes, note) {
        return { name: row.name, approve: yes ? 1 : 0, note: note || "" };
      }
    }
  };

  /* 042 AC-19, review F2. Taking your own request back. It is NOT in ACTIONS
     because it is not a decision on somebody else's document and it has one
     button, not two: the server checks the request is the caller's own and is
     still a draft (`attendance_correction.withdraw`), and the row carries
     `can_withdraw` from the same condition.

     Only attendance corrections can be withdrawn today. Leave and shift changes
     send `can_withdraw: false`, so their rows get no button - the flag decides,
     not a list of kinds held here as well. */
  var WITHDRAW = "alvoraa_portal.attendance_correction.withdraw";


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
      allClear: __("All clear."),
      failed: __("The waiting list could not load. Try again."),
      approve: __("Approve"),
      decline: __("Decline"),
      why: __("Please say why, so the person knows what to do next."),
      /* There is deliberately no "This one has already been decided." here any
         more. The server says that sentence itself, and a second copy on the
         client is a second thing to keep in step.

         A failed decision is also not always a race. A timeout, a
         dropped connection or a server error must not tell somebody their
         request was handled by a colleague - they would walk away believing
         the leave is settled. */
      couldNotDecide: __("That did not go through. Nothing has changed. Try again."),
      withdraw: __("Withdraw"),
      withdrawn: __("Request withdrawn."),
      couldNotWithdraw: __("The request could not be withdrawn. Nothing has changed. Try again.")
    };

    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);

    return ctx.api(INBOX, {}).then(function (box) {
      skeleton(false);
      if (!box) { return ctx.showState("error", SAY.failed, function () { draw(ctx); }); }
      var parts = (box.parts || []).filter(function (p) { return p.count > 0; });
      /* A part with nothing is not drawn; every part empty is "All clear." -
         a designed state, not an accident (042 AC-12). */
      if (!parts.length) { return ctx.showState("empty", SAY.allClear); }
      ctx.showScreen(build(parts, esc, __, SAY));
      wire(ctx, SAY);
    }).catch(function () {
      skeleton(false);
      ctx.showState("error", SAY.failed, function () { draw(ctx); });
    });
  }

  /* A route is only ever one of the fixed strings in `inbox_api.PARTS`, all of
     which look like "#time/fix". Anything else is not turned into a link at
     all, rather than trusted and escaped: a link is a thing a person clicks, so
     this fails closed. */
  function routeHref(route) {
    return (typeof route === "string" && /^#[a-z0-9/_-]+$/.test(route)) ? route : "";
  }

  function build(parts, esc, __, SAY) {
    var html = '<section class="nf-screen nf-inbox">';
    parts.forEach(function (part) {
      /* 042 review F6. The server sends every part's route and nothing used
         it, so four of the six parts drew rows with no buttons AND no way
         through to the screen that can act on them - "2 policies to read and
         accept" with no way to read one. The card title is that way through. */
      var href = routeHref(part.route);
      var heading = href
        ? '<a class="nf-card-link" href="' + esc(href) + '">' + esc(part.label)
          + '<span class="nf-card-link-go" aria-hidden="true"> →</span></a>'
        : esc(part.label);
      html += '<section class="nf-card" data-part="' + esc(part.key) + '">'
        + '<h2 class="nf-card-title">' + heading + "</h2>";
      /* Where the list is capped and the count is not, the screen says so. No
         part ever shows "50+", because a "50+" cannot be added into one honest
         total (042 AC-11). */
      if (part.capped) {
        html += '<p class="nf-card-note">'
          + esc(__("Showing the first {0} of {1}.", [part.shown, part.count]))
          + "</p>";
      }
      html += '<ul class="nf-rows">';
      (part.rows || []).forEach(function (row) {
        html += rowHtml(part, row, esc, SAY);
      });
      html += "</ul></section>";
    });
    return html + "</section>";
  }

  function rowHtml(part, row, esc, SAY) {
    /* 042 review F2. `row.kind` is an INTERNAL KEY - "attendance_fix",
       "shift_request" - and it used to be the last fallback here, so an
       employee's own requests were headed with it, untranslated. The server
       now sends a translated `title` for those rows. The remaining fallback is
       the part's own label, which is a translated sentence; a raw key can no
       longer reach the screen from here. */
    var title = esc(row.employee_name || row.title || part.label || "");
    var when = row.from_date
      ? esc(row.from_date) + (row.to_date && row.to_date !== row.from_date
                              ? " – " + esc(row.to_date) : "")
      : "";
    var sub = "";
    /* The context line is a NUMBER and never a colleague's name or leave type
       (042 AC-28). It is built on the server; this only draws it. */
    if (row.context) { sub += '<span class="nf-row-sub">' + esc(row.context) + "</span>"; }
    if (row.says) { sub += '<span class="nf-row-sub">' + esc(row.says) + "</span>"; }
    if (row.note) { sub += '<span class="nf-row-sub">' + esc(row.note) + "</span>"; }

    var buttons = "";
    if (ACTIONS[part.key]) {
      buttons = '<span class="nf-row-acts">'
        + '<button type="button" class="nf-btn nf-btn-small nf-decide" data-yes="1"'
        + ' data-name="' + esc(row.name) + '">' + esc(SAY.approve) + "</button>"
        + '<button type="button" class="nf-btn nf-btn-small nf-decide" data-yes="0"'
        + ' data-name="' + esc(row.name) + '">' + esc(SAY.decline) + "</button>"
        + "</span>";
    } else if (row.can_withdraw) {
      /* 042 AC-19, review F2. US-6's whole point: Rahul raises a correction by
         mistake and takes it back himself instead of asking HR. The server
         decides whether he may (`can_withdraw`); this draws it. */
      buttons = '<span class="nf-row-acts">'
        + '<button type="button" class="nf-btn nf-btn-small nf-withdraw"'
        + ' data-name="' + esc(row.name) + '">' + esc(SAY.withdraw) + "</button>"
        + "</span>";
    }
    return '<li class="nf-row" data-name="' + esc(row.name) + '">'
      + '<span class="nf-row-main"><span class="nf-row-title">' + title + "</span>"
      + (when ? '<span class="nf-row-sub">' + when + "</span>" : "")
      + sub + "</span>" + buttons + "</li>";
  }

  function wire(ctx, SAY) {
    Array.prototype.forEach.call(document.querySelectorAll(".nf-decide"),
      function (btn) {
        btn.addEventListener("click", function () {
          var part = btn.closest("[data-part]").getAttribute("data-part");
          var spec = ACTIONS[part];
          if (!spec) { return; }
          var yes = btn.getAttribute("data-yes") === "1";
          var note = "";
          if (!yes) {
            /* A decline needs a reason on EVERY path (042 AC-19, PRIV-7). The
               server enforces it too; this only saves a round trip. */
            note = window.prompt ? (window.prompt(SAY.why) || "") : "";
            if (!note.trim()) { return ctx.toast(SAY.why, "bad"); }
          }
          var row = btn.closest(".nf-row");
          btn.disabled = true;
          ctx.api(spec.approve,
                  spec.args({ name: btn.getAttribute("data-name") }, yes, note))
            .then(function () {
              if (row) { row.remove(); }
              /* Re-read, never decrement (042 AC-13). */
              return ctx.reloadCounts();
            })
            .then(function () { draw(ctx); })
            .catch(function (err) {
              /* 042 review F5. This used to say "This one has already been
                 decided." for ANY rejection and remove the row. So a timeout on
                 a factory-floor phone told Sandeep a colleague had handled the
                 leave, took the row off his screen, and did not redraw - and he
                 walked away believing it was settled. It was not.

                 A conflict is the sentence; anything else is an error with a
                 way forward. Either way the screen is redrawn from the server,
                 so what he is looking at is true (AC-18). */
              btn.disabled = false;
              var said = serverSaid(err);
              ctx.toast(said || SAY.couldNotDecide, said ? "" : "bad");
              return ctx.reloadCounts().then(function () { draw(ctx); });
            });
        });
      });

    Array.prototype.forEach.call(document.querySelectorAll(".nf-withdraw"),
      function (btn) {
        btn.addEventListener("click", function () {
          btn.disabled = true;
          ctx.api(WITHDRAW, { name: btn.getAttribute("data-name") })
            .then(function () {
              ctx.toast(SAY.withdrawn);
              return ctx.reloadCounts();
            })
            .then(function () { draw(ctx); })
            .catch(function (err) {
              /* The same honesty as the decide path: nothing is removed from
                 the screen on a failure, the server's own sentence is shown
                 where there is one - "HR has already decided this one, so it
                 cannot be withdrawn." - and the screen is re-read so it shows
                 what the server actually holds. */
              btn.disabled = false;
              var said = serverSaid(err);
              ctx.toast(said || SAY.couldNotWithdraw, said ? "" : "bad");
              return ctx.reloadCounts().then(function () { draw(ctx); });
            });
        });
      });
  }

  /* Was this refusal "somebody decided it first", or was it a timeout, a
     dropped connection or a server fault?

     The client does not guess. `attendance_correction.decide` already throws
     the sentence "This one has already been decided." and `next-frame.api`
     already carries the server's own sentence through on `err.message`. So the
     rule is: if the server said something, say what the server said; if it said
     nothing, it never answered, and the person is told that instead.

     That is why the client-side copy of the conflict sentence is gone. Two
     places holding the same sentence is two places that can disagree, and the
     one that was wrong was the client - it said "already decided" for every
     failure, including the ones where nothing had been decided at all.

     A refusal with no sentence fails closed to the error state: one extra
     retry costs a tap, and the other wrong guess costs a leave request nobody
     approves. */
  function serverSaid(err) {
    if (!err) { return ""; }
    /* `exc_type` is set only when the APPLICATION raised - Frappe puts it on
       the body beside the sentence in `_server_messages`. A 504 from a proxy,
       a 502, a dropped connection: no `exc_type`, and no sentence either.
       Without this gate `err.message` falls back to `res.statusText`, so a
       gateway timeout would show a person the word "Gateway Timeout" - or, in
       the harness that caught this, the bare number 504. */
    if (!err.exc_type) { return ""; }
    var said = typeof err.message === "string" ? err.message.trim() : "";
    return said === "Request failed" ? "" : said;
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("inbox", draw);
  }
  window.NextInbox = { draw: draw, build: build };
})();
