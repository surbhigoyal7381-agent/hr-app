/* Slice 045, Wave 4: the Team screen - two sections, and the eleven-row matrix.
 *
 * Its own static file, like every other panel. OPS-31 made the split free.
 *
 * What this file may do: ask `team_api.get_team`, and draw the answer.
 * What it may not do: decide anything. Not a section, not a permission, not a
 * count.
 *
 * **Three rules, and all three are about not repeating the server.**
 *
 * 1. **Two sections, never one list with a label.** "Your team" is the people
 *    who report to this caller; "You cover" is their HR scope minus those. A
 *    screen is scanned by shape before it is read, so two headings say "these
 *    are two different relationships" before anybody reads a name. A chip on a
 *    row in one long list has to be read forty-two times.
 *
 * 2. **The actions come from the row.** `row.actions` is the server's answer
 *    to the eleven-row matrix for THAT person. This file draws what is in that
 *    array and nothing else. It never asks "is this the covered section, so
 *    hide Approve" - that would be a second copy of the matrix, in a browser,
 *    where it can be edited. A control that is absent cannot be pressed; a
 *    control that is merely disabled can be re-enabled from a console, and
 *    `01b` §14 rule 1 forbids a greyed control anyway.
 *
 * 3. **Each count belongs to its own section, and says so when capped.** There
 *    is no combined total anywhere, because there is no single list on this
 *    screen a combined total could equal. The number in a heading is the length
 *    of the array the rows beneath it were drawn from - taken from that array,
 *    not from a second key that could drift.
 *
 * **What is honestly not built yet, said here rather than hidden in a
 * button.** Four of the eleven rows lead to a person screen Wave 4 does not
 * build (`open_record`, `see_presence`, `see_scorecard`, and the two phone and
 * deduction controls). They are still LISTED on the person's sheet, because
 * they are things the caller may do and hiding them would be a lie about their
 * access - but they are listed as text with the screen that owns them named,
 * not as a button that does nothing. A button that silently does nothing is
 * the worst of the three possible behaviours.
 *
 * **Nothing from the server reaches innerHTML unescaped.** Designation and
 * department are tenant-editable text (AC-85).
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-team";
  var TEAM = "alvoraa_portal.team_api.get_team";

  /* The eleven rows, as the server names them, with the words a person reads.
     A name the server sends that is NOT in here is drawn with its own name
     rather than skipped - a silently dropped action is a permission that was
     granted and never reached the screen. */
  function actionWords(ctx) {
    var __ = ctx.__;
    return {
      approve_leave: __("Approve or decline leave"),
      see_leave_why: __("See why they asked"),
      approve_correction: __("Decide an attendance fix"),
      approve_evidence: __("Approve goal evidence"),
      set_goals: __("Set or change goals"),
      see_scorecard: __("See their scorecard"),
      see_presence: __("See who is in today"),
      open_record: __("Open their record"),
      invite_or_block_phone: __("Invite or block their phone"),
      cancel_deduction: __("Cancel an attendance deduction"),
      /* Never plain "Approve" on a covered row. An HR override is the same
         outcome as a manager's approval and a different act, and the record
         has to be able to tell them apart a year later (AC-82). */
      act_as_hr: __("Approve as HR")
    };
  }

  /* Where each action is done today. An action with no entry here is listed
     with the sentence below instead of being offered as a control. */
  var GOES_TO = {
    approve_leave: "inbox",
    see_leave_why: "inbox",
    approve_correction: "inbox",
    approve_evidence: "inbox",
    act_as_hr: "inbox",
    set_goals: "growth"
  };

  function words(ctx) {
    var __ = ctx.__;
    return {
      yourTeam: __("Your team"),
      youCover: __("You cover"),
      noScope: __("Nobody is in your scope yet. Ask whoever set up your access."),
      cardFailed: __("This could not load."),
      canDo: __("What you can do"),
      elsewhere: __("Also yours to do"),
      elsewhereNote: __("These are still on the older screens. Open them from the menu."),
      nothing: __("There is nothing you can do for this person from here."),
      /* Whole phrases with placeholders - never a sentence built by joining
         pieces, because the figures move in word order between English, Hindi
         and Punjabi. */
      heading: function (label, n) { return __("{0} ({1})", [label, n]); },
      capped: function (label, shown, total) {
        return __("{0} — showing the first {1} of {2}", [label, shown, total]);
      }
    };
  }

  /* ── the screen ──────────────────────────────────────────────────────────── */

  function draw(ctx) {
    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);
    return ctx.api(TEAM, {}).then(function (data) {
      skeleton(false);
      if (data && data.no_employee) {
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + ctx.esc(ctx.SAY.noEmployee) + "</p></section>");
      }
      ctx.showScreen(build(data, ctx));
      wire(data, ctx);
    }).catch(function (reason) {
      skeleton(false);
      var said = refusalSentence(reason);
      if (said) {
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + ctx.esc(said) + "</p></section>");
      }
      ctx.showState("page-error", ctx.SAY.pageFailed(ctx.errorCode()),
                    function () { draw(ctx); });
    });
  }

  function skeleton(on) {
    var node = document.getElementById(SKELETON);
    if (node) { node.hidden = !on; }
  }

  /* The server's own sentence where there is one. The type is checked as well
     as the message, because with no sentence the frame falls back to the status
     text, and "Forbidden" is not something to show anybody. */
  function refusalSentence(err) {
    if (!err || !err.message) { return ""; }
    var worded = err.exc_type === "PermissionError"
      || err.exc_type === "ValidationError"
      || err.exc_type === "DoesNotExistError";
    return worded ? err.message : "";
  }

  function build(data, ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    var html = "";
    /* `has_direct` and `has_covered` are the server's answer to "does this
       heading exist". Read from the payload rather than worked out from the
       length of an array, so nobody ever sees an empty heading (AC-73). */
    if (data.has_direct) { html += section(SAY.yourTeam, data.direct, ctx, SAY); }
    if (data.has_covered) { html += section(SAY.youCover, data.covered, ctx, SAY); }
    if (!html) {
      /* AC-49, and this is W1D-20's must-not-break case: a store's HR person
         with no direct reports is NOT an empty screen, she is her store. This
         line is reached only when the scope genuinely holds nobody. */
      html = '<p class="nf-screen-note">' + esc(SAY.noScope) + "</p>";
    }
    return '<section class="nf-screen nf-team">' + html + "</section>";
  }

  function section(label, part, ctx, SAY) {
    var esc = ctx.esc;
    var rows = (part && part.rows) || [];
    /* **The number in the heading is the length of the array beneath it.**
       Not `part.total` - that is the TRUE total, and it is said separately
       when the list is capped. A heading showing the true total above a
       shorter list is the one thing worse than no number at all. */
    var heading = part.capped
      ? SAY.capped(label, rows.length, part.total)
      : SAY.heading(label, rows.length);
    var html = '<section class="nf-card"><h2 class="nf-card-title">'
      + esc(heading) + '</h2><ul class="nf-people">';
    rows.forEach(function (row) { html += person(row, ctx); });
    return html + "</ul></section>";
  }

  function person(row, ctx) {
    var esc = ctx.esc;
    var sub = [row.designation, row.department]
      .filter(function (s) { return !!s; }).join(" · ");
    /* A button, not a link: it opens a sheet rather than going anywhere, and a
       link that does not navigate is a lie to a screen reader. */
    return '<li class="nf-person">'
      + '<button type="button" class="nf-person-btn" data-person="'
      + esc(row.name) + '">'
      + '<span class="nf-avatar" aria-hidden="true">'
      + esc(ctx.initials(row.employee_name)) + "</span>"
      + '<span><span class="nf-person-name">' + esc(row.employee_name) + "</span>"
      + '<span class="nf-person-sub">' + esc(sub) + "</span></span>"
      /* The number of things this caller may do, so the row says how much is
         behind it before it is opened. It is the length of the list the sheet
         draws, taken from the same array. */
      + '<span class="nf-person-count">' + esc(String((row.actions || []).length))
      + "</span></button></li>";
  }

  /* ── the person sheet ────────────────────────────────────────────────────── */

  /* The frame's sheet, not a second copy of it: it has the focus trap, Escape,
     the title that takes focus and the return of focus to the control that
     opened it (AC-34, AC-9). */
  function openPerson(row, ctx, opener) {
    var esc = ctx.esc, SAY = words(ctx), NAMES = actionWords(ctx);
    var list = row.actions || [];
    var here = list.filter(function (a) { return !!GOES_TO[a]; });
    var elsewhere = list.filter(function (a) { return !GOES_TO[a]; });

    var html = "";
    if (!list.length) {
      html = '<p class="nf-sheet-lead">' + esc(SAY.nothing) + "</p>";
    }
    if (here.length) {
      html += '<h3 class="nf-card-title">' + esc(SAY.canDo) + "</h3>"
        + '<div class="nf-sheet-acts">';
      here.forEach(function (act) {
        html += '<button type="button" class="nf-btn" data-act="' + esc(act)
          + '">' + esc(NAMES[act] || act) + "</button>";
      });
      html += "</div>";
    }
    if (elsewhere.length) {
      /* Listed, not offered. These are things the caller may do - hiding them
         would be a lie about their access - but the screen that does them is
         not this one, and a button that goes nowhere is worse than a sentence
         that says where to go. */
      html += '<h3 class="nf-card-title">' + esc(SAY.elsewhere) + "</h3>"
        + '<ul class="nf-rows">';
      elsewhere.forEach(function (act) {
        html += '<li class="nf-row"><span class="nf-row-main">'
          + '<span class="nf-row-title">' + esc(NAMES[act] || act)
          + "</span></span></li>";
      });
      html += '</ul><p class="nf-card-note">' + esc(SAY.elsewhereNote) + "</p>";
    }

    ctx.openSheet(row.employee_name || "", html, function (bodyNode) {
      Array.prototype.forEach.call(
        bodyNode.querySelectorAll("[data-act]"), function (node) {
          node.addEventListener("click", function () {
            ctx.closeSheet();
            ctx.go(GOES_TO[node.getAttribute("data-act")]);
          });
        });
    }, opener);
  }

  function wire(data, ctx) {
    var root = document.getElementById("nf-screens") || document;
    var byId = {};
    [data.direct, data.covered].forEach(function (part) {
      ((part && part.rows) || []).forEach(function (row) { byId[row.name] = row; });
    });
    Array.prototype.forEach.call(
      root.querySelectorAll("[data-person]"), function (node) {
        node.addEventListener("click", function () {
          var row = byId[node.getAttribute("data-person")];
          if (row) { openPerson(row, ctx, node); }
        });
      });
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("team", draw);
  }
  window.NextTeam = {
    draw: draw,
    build: build,
    section: section,
    openPerson: openPerson
  };
})();
