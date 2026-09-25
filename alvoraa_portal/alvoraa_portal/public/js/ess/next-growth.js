/* Slice 045, Wave 4: Growth - goals and reviews, and the self-review wizard.
 *
 * Two routes, one file: `#growth` is the screen, `#growth/review` is the
 * wizard. They share the drawing helpers, and neither computes anything.
 *
 * **The four rules this file exists to keep.**
 *
 * 1. **The approved figure and the waiting one never meet.** A goal at 28.4
 *    with 3.1 waiting shows **28.4**, and names the 3.1 on its own line. There
 *    is no line here that adds them, and the server sends them as two keys so
 *    that there is nothing to add. `01b` §7.2: "the figure above does not move
 *    until it is approved, so nobody sees a number that has not been checked".
 *
 * 2. **Whole points.** The rating control is five buttons, not a slider. A
 *    slider that snaps is a control that can be un-snapped from a console, and
 *    the server refuses a half-point anyway - this is the screen agreeing with
 *    it rather than a second rule.
 *
 * 3. **Every company value is rated, and the list comes from the tenant.**
 *    Nothing here counts five. The fixture uses seven; a tenant with three
 *    gets three. The step is done when every value has a rating, and that
 *    answer comes from the server's `steps_answered`, so "step 3 of 5" can
 *    never mean "three steps were opened".
 *
 * 4. **The byte budget is watched while somebody is typing.** `page_data` is
 *    65,535 BYTES in strict mode, so an oversize write THROWS - and the write
 *    is an autosave, which means without a warning an employee keeps typing
 *    while nothing is being saved and nothing tells them. So this file counts
 *    the UTF-8 bytes of what is in the form itself, shows the room left
 *    **in the characters they are actually typing**, and refuses to send once
 *    it is gone. The server checks again and has the final word.
 *
 * **What the design pass may still change** (Surbhi approved one, and it has
 * not happened): the step ORDER, the look of the rating control, and how a
 * long value list is laid out on a phone. The order is `data.steps` from the
 * server for exactly that reason. **What it may not change without a new
 * decision:** the byte budget, the whole-point rule, and that every value is
 * rated.
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-growth";
  var GROWTH = "alvoraa_portal.growth_api.get_growth";
  var REVIEW = "alvoraa_portal.growth_api.get_self_review";
  var SAVE = "alvoraa_portal.growth_api.save_self_review";
  var SUBMIT = "alvoraa_portal.performance_api.submit_employee_review";

  /* The review is still a draft in these two states, and in no others. The
     SERVER decides whether a send is allowed; this only decides what to draw,
     so a review that has been sent never shows an editable wizard. */
  var DRAFT = { "Not Started": 1, "Employee Review": 1 };

  /* The wizard's state while it is open. Reset on every load, so a second
     visit never shows the first visit's answers. */
  var review = null;      /* the payload */
  var answers = {};       /* what has been typed, keyed as the server keys it */
  var step = 0;
  var saveTimer = null;
  var lastSent = "";
  var lastSaveAt = 0;

  /* AC-37: a save after a pause in typing, and never more often than this. */
  var IDLE_MS = 4000;
  var MIN_GAP_MS = 15000;

  function words(ctx) {
    var __ = ctx.__;
    return {
      noCycle: __("There is no review running right now. Your goals are below."),
      noGoals: __("No goals have been set for you yet. Ask your manager."),
      goals: __("Your goals"),
      needsAttention: __("Needs attention"),
      selfReview: __("Your self-review"),
      open: __("Open your self-review"),
      target: __("Target"),
      approved: __("Approved so far"),
      notSet: __("Not set yet"),
      cardFailed: __("This could not load."),
      noManager: __("Nobody is recorded as your manager, so there is nobody to send this to. Ask HR to set one."),
      values: __("Company values"),
      rate: __("Your rating"),
      comment: __("Anything to add? (optional)"),
      back: __("Back"),
      next: __("Next"),
      saved: __("Saved"),
      saving: __("Saving…"),
      openItems: __("Still open from last time"),
      nextPeriod: __("What you want to take on next"),
      overall: __("Anything else"),
      tooLong: __("This is too long to save. Shorten your longest answer."),
      /* The last step used to end with a Back button and nothing else, which
         reads as "you have finished" when nothing had been sent. It sends now
         (US-21), and the sentence says what pressing it does. */
      lastStep: __("Your answers are saved as you type. Nothing reaches your manager until you press Send."),
      send: __("Send to your manager"),
      sending: __("Sending\u2026"),
      sent: __("Sent. Your manager has your review now."),
      sentNote: __("You cannot change it now. If something is wrong, ask your manager to send it back."),
      /* D-13's default, said out loud rather than enforced: the three written
         steps may be left empty, and the person is told which ones are. */
      blankNote: function (steps) {
        return __("You are leaving these empty: {0}. That is allowed - send when you are ready.",
                  [steps]);
      },
      /* Whole phrases with placeholders. Never a sentence built by joining
         pieces: the figures move in word order between English, Hindi and
         Punjabi. */
      waiting: function (amount, who) {
        return __("{0} is waiting for {1}. The figure above does not move until it is approved.",
                  [amount, who]);
      },
      asOf: function (state, date) { return __("{0}, as of {1}", [state, date]); },
      stepOf: function (n, total) { return __("Step {0} of {1}", [n, total]); },
      goesTo: function (who) { return __("This goes to {0}.", [who]); },
      roomLeft: function (n) { return __("About {0} characters left.", [n]); },
      overBy: function (n) {
        return __("About {0} characters too long. Shorten your longest answer and it will save again.", [n]);
      },
      savedAt: function (t) { return __("Saved at {0}", [t]); },
      valueOf: function (n, total) { return __("Value {0} of {1}", [n, total]); }
    };
  }

  function skeleton(on) {
    var node = document.getElementById(SKELETON);
    if (node) { node.hidden = !on; }
  }

  function refusalSentence(err) {
    if (!err || !err.message) { return ""; }
    var worded = err.exc_type === "PermissionError"
      || err.exc_type === "ValidationError"
      || err.exc_type === "DoesNotExistError";
    return worded ? err.message : "";
  }

  function fail(ctx, reason, again) {
    skeleton(false);
    var said = refusalSentence(reason);
    if (said) {
      return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
        + ctx.esc(said) + "</p></section>");
    }
    ctx.showState("page-error", ctx.SAY.pageFailed(ctx.errorCode()), again);
  }

  /* ── the Growth screen ───────────────────────────────────────────────────── */

  function draw(ctx) {
    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);
    return ctx.api(GROWTH, {}).then(function (data) {
      skeleton(false);
      if (data && data.no_employee) {
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + ctx.esc(ctx.SAY.noEmployee) + "</p></section>");
      }
      ctx.showScreen(build(data, ctx));
      wireScreen(ctx);
    }).catch(function (reason) {
      fail(ctx, reason, function () { draw(ctx); });
    });
  }

  function build(data, ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    var html = '<section class="nf-screen nf-growth">';

    /* AC-43. No cycle is a SENTENCE, and the goals still render underneath it.
       Never an empty wizard, and never a spinner that stops. */
    if (!data.cycle) {
      html += '<p class="nf-screen-note">' + esc(SAY.noCycle) + "</p>";
    } else {
      html += '<section class="nf-card"><h2 class="nf-card-title">'
        + esc(data.cycle.cycle_name) + "</h2>"
        + '<p class="nf-card-note">' + esc(data.cycle.start_date) + " – "
        + esc(data.cycle.end_date) + "</p>"
        + reviewLine(data, esc, SAY) + "</section>";
    }

    if (!data.goals.length) {
      /* AC-44. The sentence, and the cycle header above it still renders. */
      html += '<p class="nf-screen-note">' + esc(SAY.noGoals) + "</p>";
      return html + "</section>";
    }

    if (data.needs_attention.length) {
      /* The count and the list are the same array, so they cannot disagree. */
      html += '<section class="nf-card"><h2 class="nf-card-title">'
        + esc(SAY.needsAttention + " (" + data.needs_attention.length + ")")
        + '</h2><ul class="nf-rows">';
      data.goals.forEach(function (goal) {
        if (!goal.trajectory.needs_attention) { return; }
        html += '<li class="nf-row"><span class="nf-row-main">'
          + '<span class="nf-row-title">' + esc(goal.goal_name) + "</span>"
          + '<span class="nf-row-sub">' + esc(chip(goal.trajectory, SAY))
          + "</span></span></li>";
      });
      html += "</ul></section>";
    }

    html += '<section class="nf-card"><h2 class="nf-card-title">'
      + esc(SAY.goals) + "</h2>";
    data.goals.forEach(function (goal) { html += goalCard(goal, esc, SAY); });
    html += "</section>";
    return html + "</section>";
  }

  function reviewLine(data, esc, SAY) {
    var block = data.review || {};
    var html = "";
    if (!block.has_manager) {
      /* AC-59. Said here, rather than discovered when Send refuses. */
      html += '<p class="nf-card-note">' + esc(SAY.noManager) + "</p>";
    } else if (block.goes_to) {
      html += '<p class="nf-card-note">' + esc(SAY.goesTo(block.goes_to)) + "</p>";
    }
    if (block.can_open) {
      html += '<div class="nf-sheet-acts"><button type="button" class="nf-btn"'
        + ' id="nf-growth-open">' + esc(SAY.open) + "</button></div>";
    }
    return html;
  }

  /* The chip. **Colour is never the only signal**: the state is words, and a
     stale one carries the date it was worked out rather than being presented
     as today's fact (AC-24, `01b` §14 rule 12). */
  function chip(trajectory, SAY) {
    if (!trajectory.state) { return SAY.notSet; }
    return trajectory.stale && trajectory.as_of
      ? SAY.asOf(trajectory.state, trajectory.as_of)
      : trajectory.state;
  }

  function goalCard(goal, esc, SAY) {
    var html = '<div class="nf-goal"><p class="nf-row-title">'
      + esc(goal.goal_name) + "</p>"
      + '<p class="nf-card-note" data-chip="' + esc(goal.goal) + '">'
      + esc(chip(goal.trajectory, SAY)) + "</p>";
    if (goal.target !== null && goal.target !== undefined && goal.target !== "") {
      html += '<p class="nf-card-note">' + esc(SAY.target) + ": "
        + esc(num(goal.target)) + " " + esc(goal.unit || "") + "</p>";
    }
    html += figures(goal, esc, SAY);
    (goal.kpis || []).forEach(function (kpi) {
      html += '<p class="nf-row-sub">' + esc(kpi.kpi_name) + "</p>"
        + figures(kpi, esc, SAY);
    });
    return html + "</div>";
  }

  /* **The two figures, as two lines.** The approved one is the headline; the
     waiting one is named underneath it. Nothing here adds them, and the server
     sent them as separate keys so there is nothing to add (AC-29). */
  function figures(row, esc, SAY) {
    var html = "";
    if (row.approved !== null && row.approved !== undefined && row.approved !== "") {
      html += '<p class="nf-growth-big">' + esc(num(row.approved)) + " "
        + esc(row.unit || "") + "</p>"
        + '<p class="nf-card-note">' + esc(SAY.approved) + "</p>";
    }
    (row.waiting || []).forEach(function (wait) {
      html += '<p class="nf-card-note nf-growth-waiting">'
        + esc(SAY.waiting(num(wait.amount) + " " + (row.unit || ""),
                          wait.logged_by || "")) + "</p>";
    });
    return html;
  }

  function num(v) {
    if (v === null || v === undefined || v === "") { return ""; }
    return String(Math.round(Number(v) * 100) / 100);
  }

  function wireScreen(ctx) {
    var open = document.getElementById("nf-growth-open");
    if (open) {
      open.addEventListener("click", function () { ctx.go("growth/review"); });
    }
  }

  /* ── the self-review wizard ──────────────────────────────────────────────── */

  function drawReview(ctx) {
    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);
    return ctx.api(REVIEW, {}).then(function (data) {
      skeleton(false);
      review = data;
      answers = (data && data.answers) || {};
      step = 0;
      lastSent = JSON.stringify(answers);
      if (!data || !data.appraisal) {
        return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
          + ctx.esc((data && data.note) || words(ctx).noCycle) + "</p></section>");
      }
      paint(ctx);
    }).catch(function (reason) {
      fail(ctx, reason, function () { drawReview(ctx); });
    });
  }

  function paint(ctx) {
    /* A review that has been sent is not an editable wizard. The server
       refuses a second send either way; this is so the screen never offers
       one. */
    if (review && !DRAFT[review.review_status]) {
      ctx.showScreen(sentScreen(ctx));
      return;
    }
    ctx.showScreen(buildReview(ctx));
    wireReview(ctx);
    showRoom(ctx);
  }

  function buildReview(ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    var steps = review.steps || [];
    var which = steps[step];
    var html = '<section class="nf-screen nf-growth-wizard">'
      /* "Step 3 of 5" counts steps that have ANSWERS, and the answer comes
         from the server (AC-28). A step that was merely opened is not
         progress, and a progress bar that says otherwise is the kind of number
         this project keeps having to apologise for. */
      + '<p class="nf-card-note" id="nf-wiz-progress">'
      + esc(SAY.stepOf((review.steps_answered || []).length, steps.length))
      + "</p>"
      + '<section class="nf-card"><h2 class="nf-card-title" id="nf-wiz-title">'
      + esc(stepTitle(which, SAY)) + "</h2>"
      + '<div id="nf-wiz-body">' + stepBody(which, ctx, SAY) + "</div></section>"
      + '<p class="nf-card-note" id="nf-wiz-room" role="status"></p>';
    var last = step === steps.length - 1;
    if (last) {
      var blank = blankOptional();
      if (blank.length) {
        html += '<p class="nf-screen-note" id="nf-wiz-blank">'
          + esc(SAY.blankNote(blank.map(function (which) {
            return stepTitle(which, SAY);
          }).join(", "))) + "</p>";
      }
      html += '<p class="nf-screen-note">' + esc(SAY.lastStep) + "</p>";
    }
    html += '<div class="nf-sheet-acts">';
    if (step > 0) {
      html += '<button type="button" class="nf-btn" id="nf-wiz-back">'
        + esc(SAY.back) + "</button>";
    }
    if (step < steps.length - 1) {
      html += '<button type="button" class="nf-btn" id="nf-wiz-next">'
        + esc(SAY.next) + "</button>";
    }
    if (last) {
      /* **Never disabled.** A missing rating is refused by the SERVER, with a
         sentence naming what is missing - a greyed-out button that says
         nothing is how somebody stands there wondering which step they
         missed. */
      /* `nf-btn` IS the primary style in this stylesheet - there is no
         "main" variant, and a class the CSS does not define is a promise
         nobody keeps. The wizard's look is D-8's design pass. */
      html += '<button type="button" class="nf-btn" id="nf-wiz-send">'
        + esc(SAY.send) + "</button>";
    }
    return html + "</div></section>";
  }

  /* Which of the OPTIONAL steps are still empty, worked out from what is on
     screen right now so the person sees it as they type. **The server sends
     `required_steps`** - this never decides what may be sent, only what to
     say. */
  function blankOptional() {
    /* No list from the server means say nothing. Guessing which steps are
       optional would be a second copy of a rule the server owns, and a wrong
       guess here tells somebody they are leaving their ratings blank. */
    if (!review.required_steps) { return []; }
    var required = {};
    review.required_steps.forEach(function (which) { required[which] = 1; });
    return (review.steps || []).filter(function (which) {
      if (required[which]) { return false; }
      return !String(((answers[which] || {}).text) || "").trim();
    });
  }

  function sentScreen(ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    return '<section class="nf-screen nf-growth-wizard">'
      + '<section class="nf-card"><h2 class="nf-card-title">' + esc(SAY.sent)
      + "</h2>"
      + '<p class="nf-card-note">' + esc(SAY.sentNote) + "</p></section></section>";
  }

  function stepTitle(which, SAY) {
    return {
      goals: SAY.goals,
      values: SAY.values,
      open_items: SAY.openItems,
      next: SAY.nextPeriod,
      overall: SAY.overall
    }[which] || which;
  }

  function stepBody(which, ctx, SAY) {
    if (which === "goals") { return goalsStep(ctx, SAY); }
    if (which === "values") { return valuesStep(ctx, SAY); }
    return textStep(which, ctx, SAY);
  }

  function goalsStep(ctx, SAY) {
    var esc = ctx.esc;
    var rows = review.goals || [];
    if (!rows.length) {
      return '<p class="nf-card-note">' + esc(SAY.noGoals) + "</p>";
    }
    var html = "";
    rows.forEach(function (goal) {
      var id = goal.name || goal.goal || "";
      html += '<div class="nf-goal"><p class="nf-row-title">'
        + esc(goal.goal_name || goal.title || "") + "</p>";
      /* The KPI figures, beside the rating, for reference. Surbhi's answer 1:
         the self-review rates GOALS, with the figures shown beside them. */
      if (goal.actual_progress !== undefined && goal.actual_progress !== null) {
        html += '<p class="nf-card-note">' + esc(SAY.approved) + ": "
          + esc(num(goal.actual_progress)) + " " + esc(goal.unit || "") + "</p>";
      }
      if (goal.target_value !== undefined && goal.target_value !== null) {
        html += '<p class="nf-card-note">' + esc(SAY.target) + ": "
          + esc(num(goal.target_value)) + " " + esc(goal.unit || "") + "</p>";
      }
      html += rating("goals", id, ctx, SAY) + comment("goals", id, ctx, SAY)
        + "</div>";
    });
    return html;
  }

  function valuesStep(ctx, SAY) {
    var esc = ctx.esc;
    var rows = review.values || [];
    var html = "";
    /* **Every** value, and the number comes from the tenant. Nothing counts
       five. Each one is numbered out loud, because seven of them on a 390 px
       screen is a scrolling problem and "Value 5 of 7" is what tells somebody
       how much is left. */
    rows.forEach(function (value, i) {
      html += '<div class="nf-goal"><p class="nf-card-note">'
        + esc(SAY.valueOf(i + 1, rows.length)) + "</p>"
        + '<p class="nf-row-title">' + esc(value.value_name || "") + "</p>";
      if (value.description) {
        html += '<p class="nf-card-note">' + esc(value.description) + "</p>";
      }
      html += rating("values", value.name, ctx, SAY)
        + comment("values", value.name, ctx, SAY) + "</div>";
    });
    return html;
  }

  /* **Whole points, as buttons.** Five controls, each one a whole number, each
     one at least 44 px (the stylesheet), each one saying its own number out
     loud. A slider that snaps to whole points is a control that can be
     un-snapped from a console; five buttons cannot produce 3.5 at all. */
  function rating(block, id, ctx, SAY) {
    var esc = ctx.esc;
    var chosen = ((answers[block] || {})[id] || {}).rating;
    var html = '<fieldset class="nf-rate"><legend class="nf-label">'
      + esc(SAY.rate) + "</legend>";
    for (var n = review.rating_min; n <= review.rating_max; n++) {
      html += '<button type="button" class="nf-rate-btn'
        + (Number(chosen) === n ? " nf-rate-on" : "") + '"'
        + ' data-rate="' + esc(String(n)) + '"'
        + ' data-block="' + esc(block) + '" data-id="' + esc(id) + '"'
        /* The state is in the accessible name as well as in the colour -
           colour is never the only signal. */
        + ' aria-pressed="' + (Number(chosen) === n ? "true" : "false") + '">'
        + esc(String(n)) + "</button>";
    }
    return html + "</fieldset>";
  }

  function comment(block, id, ctx, SAY) {
    var esc = ctx.esc;
    var value = ((answers[block] || {})[id] || {}).comment || "";
    var key = block + "::" + id;
    /* Every input has a visible label, not a placeholder - a placeholder
       disappears the moment somebody types. */
    return '<label class="nf-label" for="nf-c-' + esc(key) + '">'
      + esc(SAY.comment) + "</label>"
      + '<textarea class="nf-input" id="nf-c-' + esc(key) + '" rows="2"'
      + ' data-block="' + esc(block) + '" data-id="' + esc(id) + '">'
      + esc(value) + "</textarea>";
  }

  function textStep(which, ctx, SAY) {
    var esc = ctx.esc;
    var value = ((answers[which] || {}).text) || "";
    return '<label class="nf-label" for="nf-wiz-text">'
      + esc(stepTitle(which, SAY)) + "</label>"
      + '<textarea class="nf-input" id="nf-wiz-text" rows="6"'
      + ' data-step="' + esc(which) + '">' + esc(value) + "</textarea>";
  }

  /* ── the byte budget, watched while somebody types ───────────────────────── */

  /* The bytes this would cost, measured the way the column measures: UTF-8.

     **Counted here rather than handed to `TextEncoder`, on purpose.** The
     obvious version tries `TextEncoder` and falls back to `length * 3`. It was
     written that way first, and jsdom - which has no `TextEncoder` on its
     window - took the fallback, so the test asserting that an English
     character costs one byte got nine. That is the "jsdom is kinder than a
     browser" trap in its other form: a fork where one side is only ever
     exercised in the test and the other only ever in production. There is no
     fork now, so the number a test sees is the number a phone sees. */
  function bytesOf(text) {
    var bytes = 0;
    for (var i = 0; i < text.length; i++) {
      var code = text.charCodeAt(i);
      if (code < 0x80) { bytes += 1; }
      else if (code < 0x800) { bytes += 2; }
      else if (code >= 0xd800 && code <= 0xdbff) {
        /* A surrogate pair is ONE character in four bytes. Counting each half
           as three would make an emoji cost six and a budget too tight. */
        bytes += 4;
        i++;
      } else { bytes += 3; }
    }
    return bytes;
  }

  function roomLeft() {
    var text = JSON.stringify(answers);
    var used = bytesOf(text);
    var perCharacter = text.length ? Math.max(1, used / text.length) : 1;
    /* **In the characters they are actually typing.** A fixed divisor would
       tell a Hindi writer to cut three times more than they need to, which is
       wrong in the direction that matters. */
    return Math.floor((review.budget_bytes - used) / perCharacter);
  }

  function showRoom(ctx) {
    var node = document.getElementById("nf-wiz-room");
    if (!node || !review) { return; }
    var left = roomLeft();
    var SAY = words(ctx);
    node.textContent = left >= 0 ? SAY.roomLeft(left) : SAY.overBy(-left);
    node.setAttribute("data-over", left < 0 ? "yes" : "no");
  }

  function wireReview(ctx) {
    var root = document.getElementById("nf-screens") || document;

    Array.prototype.forEach.call(root.querySelectorAll("[data-rate]"), function (node) {
      node.addEventListener("click", function () {
        var block = node.getAttribute("data-block");
        var id = node.getAttribute("data-id");
        answers[block] = answers[block] || {};
        answers[block][id] = answers[block][id] || {};
        answers[block][id].rating = Number(node.getAttribute("data-rate"));
        paint(ctx);
        queueSave(ctx);
      });
    });

    Array.prototype.forEach.call(root.querySelectorAll("textarea[data-id]"), function (node) {
      node.addEventListener("input", function () {
        var block = node.getAttribute("data-block");
        var id = node.getAttribute("data-id");
        answers[block] = answers[block] || {};
        answers[block][id] = answers[block][id] || {};
        answers[block][id].comment = node.value;
        showRoom(ctx);
        queueSave(ctx);
      });
    });

    var text = root.querySelector("textarea[data-step]");
    if (text) {
      text.addEventListener("input", function () {
        answers[text.getAttribute("data-step")] = { text: text.value };
        showRoom(ctx);
        queueSave(ctx);
      });
    }

    var back = document.getElementById("nf-wiz-back");
    if (back) {
      back.addEventListener("click", function () {
        step = Math.max(0, step - 1);
        save(ctx);          /* on step change, always */
        paint(ctx);
      });
    }
    var next = document.getElementById("nf-wiz-next");
    if (next) {
      next.addEventListener("click", function () {
        step = Math.min((review.steps || []).length - 1, step + 1);
        save(ctx);
        paint(ctx);
      });
    }
    var sendBtn = document.getElementById("nf-wiz-send");
    if (sendBtn) {
      sendBtn.addEventListener("click", function () { doSend(ctx, sendBtn); });
    }
  }

  /* **Save first, then send.** The autosave waits for a pause in typing, so
     the last thing somebody typed may not have left the browser yet. Sending
     without this is how a Send stores everything except the last answer -
     the silent failure US-21 is about, in miniature. */
  function doSend(ctx, button) {
    var SAY = words(ctx);
    button.disabled = true;
    button.textContent = SAY.sending;
    window.clearTimeout(saveTimer);
    lastSaveAt = 0;              /* the minimum gap does not apply to a send */
    save(ctx).then(function () {
      return ctx.api(SUBMIT, { appraisal: review.appraisal, overall_comment: "" });
    }).then(function (out) {
      review.review_status = (out && out.review_status) || "Manager Review";
      paint(ctx);
    }).catch(function (reason) {
      /* The SERVER's sentence, which names what is still missing. */
      button.disabled = false;
      button.textContent = SAY.send;
      ctx.toast(refusalSentence(reason) || SAY.cardFailed, "bad");
    });
  }

  /* A save after a pause, and never more often than MIN_GAP_MS. An unchanged
     step sends nothing at all - `lastSent` is what makes that true. */
  function queueSave(ctx) {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(function () { save(ctx); }, IDLE_MS);
  }

  function save(ctx) {
    if (!review || !review.appraisal) { return Promise.resolve(); }
    var now = Date.now();
    var text = JSON.stringify(answers);
    if (text === lastSent) { return Promise.resolve(); }
    if (now - lastSaveAt < MIN_GAP_MS) { return queueSave(ctx), Promise.resolve(); }
    if (roomLeft() < 0) {
      /* **Refused here, before the call.** The server refuses it too and has
         the final word; this stops an autosave failing silently while somebody
         keeps typing. */
      showRoom(ctx);
      return Promise.resolve();
    }
    lastSaveAt = now;
    lastSent = text;
    return ctx.api(SAVE, { appraisal: review.appraisal, answers: text })
      .then(function (out) {
        /* The SERVER's confirmed time. A browser clock can be hours out, and
           "Saved at 14:02" from a wrong clock is worse than no time at all. */
        var node = document.getElementById("nf-wiz-room");
        if (node && out) {
          node.textContent = words(ctx).savedAt(String(out.saved_at).slice(11, 16))
            + " · " + words(ctx).roomLeft(out.room_left_characters);
        }
      })
      .catch(function (reason) {
        lastSent = "";   /* it did not land, so it is not the last thing sent */
        ctx.toast(refusalSentence(reason) || words(ctx).cardFailed, "bad");
      });
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("growth", draw);
    window.NextFrame.panel("growth/review", drawReview);
  }
  window.NextGrowth = {
    draw: draw,
    drawReview: drawReview,
    build: build,
    buildReview: buildReview,
    chip: chip,
    figures: figures,
    bytesOf: bytesOf,
    roomLeft: roomLeft,
    blankOptional: blankOptional,
    _state: function () { return { review: review, answers: answers, step: step }; }
  };
})();
