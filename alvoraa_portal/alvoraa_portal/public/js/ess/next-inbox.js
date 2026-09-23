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
 *   returns a refusal. When somebody else decided first, the answer is
 *   "This one has already been decided." - which is not an error state.
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
     the caller's own requests. */
  var ACTIONS = {
    leave_approvals: {
      approve: "alvoraa_portal.hr_api.action_leave",
      args: function (row, yes, note) {
        return { name: row.name, action: yes ? "approve" : "reject", reason: note || "" };
      }
    },
    attendance_fixes: {
      approve: "alvoraa_portal.attendance_correction.decide",
      args: function (row, yes, note) {
        return { name: row.name, approve: yes ? 1 : 0, note: note || "" };
      }
    }
  };


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
      decided: __("This one has already been decided."),
      mine: __("My requests"),
      waitingOnMe: __("Waiting on me"),
      withdraw: __("Withdraw")
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

  function build(parts, esc, __, SAY) {
    var html = '<section class="nf-screen nf-inbox">';
    parts.forEach(function (part) {
      html += '<section class="nf-card" data-part="' + esc(part.key) + '">'
        + '<h2 class="nf-card-title">' + esc(part.label) + "</h2>";
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
    var title = esc(row.employee_name || row.title || row.kind || "");
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
            .catch(function () {
              /* Somebody decided it first. The row goes, the counts refresh,
                 and this is not an error state (042 AC-18). */
              if (row) { row.remove(); }
              ctx.toast(SAY.decided);
              ctx.reloadCounts();
            });
        });
      });
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("inbox", draw);
  }
  window.NextInbox = { draw: draw, build: build };
})();
