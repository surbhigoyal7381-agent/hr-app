/* Slice 043, Wave 3: the Time panel - Days, Leave and the Late rule.
 *
 * Its own static file, like Home's and the Inbox's. OPS-31 made the split free,
 * and two sessions building two panels never meet in one file.
 *
 * What this file may do: ask `time_api.get_time`, and draw the answer.
 * What it may not do: decide anything. Every permission, every scope and every
 * number is the server's. No figure is computed here - not a total, not a
 * lateness, not a balance. Where a total and a list could be worked out two
 * ways, the server worked it out once and this draws both from the same array
 * (043 AC-11).
 *
 * Four rules it keeps:
 *
 *   **Nothing from the server reaches innerHTML unescaped** (042 AC-60).
 *   Everything goes through the frame's `esc`, which is handed in.
 *
 *   **Colour is never the only signal** (AC-41, §16). Every day in the grid
 *   carries its state in words in its accessible name, and every chip says its
 *   state in words. "Late by 12 min (within grace)" is neutral grey AND says
 *   "(within grace)", which is exactly why the words are there.
 *
 *   **No number and no day of the week is written into this file.** The grace
 *   figure, the late threshold, the week's start day and the weekly-off
 *   weekdays all come from records. The endpoint this wave retires hard-coded
 *   Saturday and Sunday and was wrong for every tenant that does not work that
 *   way.
 *
 *   **A card that failed says so, and the rest of the screen works** (AC-36).
 */
(function () {
  "use strict";

  var SKELETON = "nf-skeleton-time";
  var TIME = "alvoraa_portal.time_api.get_time";
  var RAISE = "alvoraa_portal.attendance_correction.raise_correction";
  var REASONS = "alvoraa_portal.attendance_correction.reasons";

  /* Which tab is showing. Held here rather than in the URL because Wave 1 owns
     the route table, and a tab is not a page: the back button should leave
     Time, not step between its tabs. */
  var tab = "days";
  /* The month being looked at. Null means "whatever the server calls today",
     so the first load never sends a date the browser worked out - AC-51: today
     is the SITE's date, not the phone's. */
  var at = null;

  function skeleton(on) {
    var node = document.getElementById(SKELETON);
    if (node) { node.hidden = !on; }
  }

  function words(ctx) {
    var __ = ctx.__;
    return {
      days: __("Days"),
      leave: __("Leave"),
      rule: __("Late rule"),
      tabs: __("Which part of Time to show"),
      prev: __("Previous month"),
      next: __("Next month"),
      cardFailed: __("This could not load."),
      noAttendance: __("No attendance was recorded this month."),
      noShift: __("No shift is set for you. Ask HR."),
      yourShift: __("Your shift"),
      daysOff: __("Days off ahead"),
      noHolidays: __("No holidays are coming up on your list."),
      leaveLeft: __("Leave left"),
      pastLeave: __("Leave taken"),
      noPastLeave: __("You have not taken any leave this year."),
      noBalances: __("No leave has been allocated to you yet."),
      record: __("Your record this year"),
      noRecord: __("Nothing has been taken off your pay this year."),
      fix: __("Fix this day"),
      onLeave: __("I was on leave"),
      close: __("Close"),
      send: __("Send"),
      reason: __("What happened?"),
      explain: __("Tell us in your own words"),
      reasonNeeded: __("Choose what happened, so whoever reviews this knows what to look for."),
      sent: __("Sent. You will see it in your inbox."),
      punches: __("Your punches"),
      noPunches: __("No punches were recorded for this day."),
      worked: __("Days worked"),
      absent: __("Days marked absent"),
      onTime: __("Arrived within grace"),
      weeklyOffs: __("Weekly offs so far"),
      holidaysTaken: __("Public holidays"),
      /* Whole sentences with placeholders. Never "Late by " + n + " min":
         Hindi and Punjabi put the number and the unit the other way round
         (AC-40). */
      lateWithin: function (n) { return __("Late by {0} min (within grace)", [n]); },
      lateBy: function (n) { return __("Late by {0} min", [n]); },
      onTimeChip: __("On time"),
      markedAbsent: __("Marked absent"),
      weeklyOff: __("Weekly off"),
      future: __("Not yet"),
      beforeJoining: __("Before you joined"),
      noRecordDay: __("Nothing recorded"),
      leaveDay: __("On leave"),
      halfDay: __("Half day"),
      graceShift: function (n, s) {
        return __("{0} minutes of grace, set on the {1} shift", [n, s]);
      },
      graceOrg: function (n, org) {
        return __("{0} minutes of grace, set by {1}", [n, org]);
      },
      noGrace: __("There is no grace period, so any late arrival counts."),
      waiting: function (who) { return __("Request sent · waiting for {0}", [who]); },
      waitingAnyone: __("Request sent · waiting to be reviewed"),
      offOn: function (list) { return __("Off on {0}", [list]); },
      takenByRule: __("Taken by the late-coming rule"),
      accountable: function (who) { return __("If you think this is wrong, contact {0}.", [who]); },
      monthOf: function (m, y) { return __("{0} {1}", [m, y]); }
    };
  }

  /* ── drawing ─────────────────────────────────────────────────────────────── */

  function draw(ctx) {
    skeleton(true);
    ctx.showState("loading", ctx.SAY.loading);
    var asked = at || {};
    return ctx.api(TIME, { year: asked.year, month: asked.month })
      .then(function (data) {
        skeleton(false);
        at = { year: data.month.year, month: data.month.month };
        ctx.showScreen(build(data, ctx));
        wire(data, ctx);
      })
      .catch(function (reason) {
        skeleton(false);
        /* AC-37. A refusal is a sentence, not an error page: somebody who
           opened a month they may not see has done nothing wrong, and a red
           page tells them they have. */
        var said = refusalSentence(reason);
        if (said) {
          return ctx.showScreen('<section class="nf-screen"><p class="nf-screen-note">'
            + ctx.esc(said) + "</p></section>");
        }
        ctx.showState("page-error", ctx.SAY.pageFailed(ctx.errorCode()),
                      function () { draw(ctx); });
      });
  }

  /* The sentence the SERVER wrote, where it wrote one. Anything else - a
     dropped connection, a 500 - has no sentence and falls through to the page
     error, which carries a code holding no personal data (AC-38).

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
    return '<section class="nf-screen nf-time">'
      + tabs(esc, SAY)
      + '<div id="nf-time-body">' + body(data, ctx, SAY) + "</div>"
      + "</section>";
  }

  function tabs(esc, SAY) {
    /* `role="tablist"` with real buttons. A person on a keyboard reaches them
       with Tab and presses them with Space, and a screen reader is told which
       one is current - which is what `aria-selected` is for. */
    var list = [["days", SAY.days], ["leave", SAY.leave], ["rule", SAY.rule]];
    var html = '<div class="nf-tabs" role="tablist" aria-label="' + esc(SAY.tabs) + '">';
    list.forEach(function (row) {
      html += '<button type="button" class="nf-tab-btn" role="tab"'
        + ' data-tab="' + esc(row[0]) + '"'
        + ' aria-selected="' + (tab === row[0] ? "true" : "false") + '">'
        + esc(row[1]) + "</button>";
    });
    return html + "</div>";
  }

  function body(data, ctx, SAY) {
    if (tab === "leave") { return leaveTab(data, ctx, SAY); }
    if (tab === "rule") { return ruleTab(data, ctx, SAY); }
    return daysTab(data, ctx, SAY);
  }

  /* ── Days ────────────────────────────────────────────────────────────────── */

  function daysTab(data, ctx, SAY) {
    var esc = ctx.esc;
    var month = data.month;
    return statistics(month, esc, SAY)
      + calendar(month, esc, SAY)
      + dayList(month, esc, SAY)
      + shiftCard(data, esc, SAY)
      + daysOffCard(data, esc, SAY);
  }

  function statistics(month, esc, SAY) {
    /* Every figure here is `month.totals`, which the server worked out from
       the same `days` array the list below renders. There is no counting in
       this file, so the number and the list it links to cannot disagree
       (AC-11). */
    var t = month.totals || {};
    var rows = [
      [SAY.worked, t.present],
      [SAY.absent, t.absent],
      [SAY.weeklyOffs, t.weekly_offs],
      [SAY.holidaysTaken, t.named_holidays]
    ];
    var html = '<section class="nf-card"><ul class="nf-counts">';
    rows.forEach(function (row) {
      if (row[1] === null || row[1] === undefined) { return; }
      html += '<li class="nf-count"><span class="nf-count-n">' + esc(String(row[1]))
        + '</span><span class="nf-count-w">' + esc(row[0]) + "</span></li>";
    });
    return html + "</ul></section>";
  }

  function calendar(month, esc, SAY) {
    var html = '<section class="nf-card nf-cal-card">'
      + '<div class="nf-cal-head">'
      + '<button type="button" class="nf-icon-btn" id="nf-cal-prev" aria-label="'
      + esc(SAY.prev) + '">&#8249;</button>'
      + '<h2 class="nf-card-title nf-cal-title" id="nf-cal-title">'
      + esc(SAY.monthOf(monthName(month.month), month.year)) + "</h2>"
      + '<button type="button" class="nf-icon-btn" id="nf-cal-next" aria-label="'
      + esc(SAY.next) + '">&#8250;</button>'
      + "</div>";

    html += '<ul class="nf-cal" role="list">';
    /* The blanks before the first of the month, so the columns line up. They
       are `aria-hidden` and are not list items a screen reader counts. */
    var lead = firstColumn(month);
    var i;
    for (i = 0; i < lead; i++) {
      html += '<li class="nf-cal-pad" aria-hidden="true"></li>';
    }
    (month.days || []).forEach(function (day) {
      html += cell(day, esc, SAY);
    });
    return html + "</ul></section>";
  }

  /* Which column the 1st sits in, with the week starting Monday - the
     prototype's choice, kept (§21 row j). This is a LAYOUT decision about the
     calendar's first column and is deliberately not the late rule's
     `week_start_day`, which is about when a week of violations begins. The
     prototype used one number for both and they are two different things. */
  function firstColumn(month) {
    var order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                 "Saturday", "Sunday"];
    var first = (month.days && month.days[0]) ? month.days[0].weekday : "Monday";
    var found = order.indexOf(first);
    return found < 0 ? 0 : found;
  }

  function monthName(n) {
    /* Drawn from the browser's own locale data rather than a list of names in
       this file, so Hindi and Punjabi get their own month names for free. */
    try {
      return new Date(2000, Number(n) - 1, 1)
        .toLocaleDateString(document.documentElement.lang || undefined,
                            { month: "long" });
    } catch (e) { return String(n); }
  }

  /* What a day IS, in one word, for the class name - and in a sentence, for
     the accessible name. Order matters: a day before somebody joined is not
     their record at all, whatever else is true of it (AC-45). */
  function dayState(day) {
    if (day.before_joining) { return "before"; }
    if (day.future) { return "future"; }
    if (day.weekly_off) { return "weeklyoff"; }
    if (day.holiday) { return "holiday"; }
    if (day.state === "absent") { return "absent"; }
    if (day.state === "on_leave" || day.state === "leave") { return "leave"; }
    if (day.state === "half_day") { return "half"; }
    if (day.state === "present" || day.state === "work_from_home") {
      return day.is_late ? "late" : "present";
    }
    return "none";
  }

  function stateWords(day, SAY) {
    var state = dayState(day);
    if (state === "before") { return SAY.beforeJoining; }
    if (state === "future") { return SAY.future; }
    if (state === "weeklyoff") { return SAY.weeklyOff; }
    if (state === "holiday") { return day.holiday; }
    /* D5: "Marked absent", NOT "No punch and no leave". The second describes
       what the system noticed; the first describes what happened to the
       person, which is the thing they can argue with. */
    if (state === "absent") { return SAY.markedAbsent; }
    if (state === "leave") { return SAY.leaveDay; }
    if (state === "half") { return SAY.halfDay; }
    if (state === "late") { return SAY.lateBy(day.late_by_mins); }
    if (state === "present") {
      /* The minutes shown are always the TRUE minutes (009 decision 7). The
         grace decides whether a day COUNTS as late, never what it says. */
      return day.late_by_mins > 0
        ? SAY.lateWithin(day.late_by_mins) : SAY.onTimeChip;
    }
    return SAY.noRecordDay;
  }

  function openable(day) {
    /* AC-3. A future day and a day before joining are not tappable: there is
       nothing to show and nothing to correct, and a control that opens an
       empty sheet teaches people the screen is broken. */
    return !day.future && !day.before_joining;
  }

  function cell(day, esc, SAY) {
    var state = dayState(day);
    var number = Number(String(day.date).slice(8, 10));
    var label = esc(day.date) + " — " + esc(stateWords(day, SAY));
    if (!openable(day)) {
      return '<li class="nf-cal-day nf-cal-' + esc(state) + ' is-flat">'
        + '<span aria-hidden="true">' + esc(String(number)) + "</span>"
        + '<span class="nf-sr">' + label + "</span></li>";
    }
    return '<li class="nf-cal-day nf-cal-' + esc(state) + '">'
      + '<button type="button" class="nf-cal-btn" data-day="' + esc(day.date) + '">'
      + '<span aria-hidden="true">' + esc(String(number)) + "</span>"
      + '<span class="nf-sr">' + label + "</span></button></li>";
  }

  function dayList(month, esc, SAY) {
    /* Only the days with something to say. A list of 31 rows of "nothing
       recorded" is a list nobody reads. */
    var rows = (month.days || []).filter(function (day) {
      var state = dayState(day);
      return state !== "none" && state !== "future" && state !== "before";
    });
    if (!rows.length) {
      return '<section class="nf-card"><p class="nf-card-note">'
        + esc(SAY.noAttendance) + "</p></section>";
    }
    var html = '<section class="nf-card"><ul class="nf-rows">';
    rows.forEach(function (day) {
      var sub = day.request
        ? '<span class="nf-row-sub">' + esc(requestLine(day, SAY)) + "</span>" : "";
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(day.date) + " · "
        + esc(stateWords(day, SAY)) + "</span>" + sub + "</span>";
      if (openable(day)) {
        html += '<span class="nf-row-acts"><button type="button"'
          + ' class="nf-btn nf-btn-small" data-day="' + esc(day.date) + '">'
          + esc(SAY.days) + "</button></span>";
      }
      html += "</li>";
    });
    return html + "</ul></section>";
  }

  /* AC-9. A day already covered by an open request says where the request got
     to, and does not offer Fix a second time. */
  function requestLine(day, SAY) {
    var who = day.request && day.request.alvoraa_reviewed_by;
    return who ? SAY.waiting(who) : SAY.waitingAnyone;
  }

  function shiftCard(data, esc, SAY) {
    var card = data.shift;
    if (!card) { return ""; }
    if (card.note || !card.shift) {
      /* AC-34. A sentence, never blank times - "your shift is nothing" is not
         a fact anybody can act on. */
      return cardBox(esc(SAY.yourShift),
                     '<p class="nf-card-note">' + esc(card.note || SAY.noShift)
                     + "</p>", esc);
    }
    var offs = (data.days_off && data.days_off.weekly_off_weekdays) || [];
    var line = esc(card.starts || "") + " – " + esc(card.ends || "");
    var off = offs.length
      ? '<p class="nf-card-note">' + esc(SAY.offOn(offs.join(", "))) + "</p>" : "";
    return cardBox(esc(SAY.yourShift),
                   '<p class="nf-hero-shift">' + line + "</p>" + off, esc);
  }

  function daysOffCard(data, esc, SAY) {
    var off = data.days_off;
    if (!off) { return ""; }
    if (off.note) {
      /* Slice 035's sentence. A setup gap says so; a quiet empty card hides
         it, and on a new tenant that gap is HR's to close. */
      return cardBox(esc(SAY.daysOff),
                     '<p class="nf-card-note">' + esc(off.note) + "</p>", esc);
    }
    if (!off.holidays || !off.holidays.length) {
      return cardBox(esc(SAY.daysOff),
                     '<p class="nf-card-note">' + esc(SAY.noHolidays) + "</p>", esc);
    }
    var html = '<ul class="nf-rows">';
    off.holidays.slice(0, 8).forEach(function (row) {
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(row.description || "") + "</span>"
        + '<span class="nf-row-sub">' + esc(row.date) + "</span></span></li>";
    });
    return cardBox(esc(SAY.daysOff), html + "</ul>", esc);
  }

  /* ── Leave ───────────────────────────────────────────────────────────────── */

  function leaveTab(data, ctx, SAY) {
    var esc = ctx.esc;
    var leave = data.leave || {};
    var html = "";

    if (!leave.balances || !leave.balances.length) {
      html += cardBox(esc(SAY.leaveLeft),
                      '<p class="nf-card-note">' + esc(SAY.noBalances) + "</p>", esc);
    } else {
      var rows = '<ul class="nf-rows">';
      leave.balances.forEach(function (row) {
        /* A fully used type is SHOWN, not hidden (042 AC-6). "0 of 8" is a
           fact somebody needs; a missing row reads as "you never had any". */
        rows += '<li class="nf-row"><span class="nf-row-main">'
          + '<span class="nf-row-title">' + esc(row.leave_type) + "</span></span>"
          + '<span class="nf-row-val">' + esc(num(row.left)) + " / "
          + esc(num(row.total)) + "</span></li>";
      });
      html += cardBox(esc(SAY.leaveLeft), rows + "</ul>", esc);
    }

    var past = leave.past || [];
    if (!past.length) {
      html += cardBox(esc(SAY.pastLeave),
                      '<p class="nf-card-note">' + esc(SAY.noPastLeave) + "</p>", esc);
      return html;
    }
    var list = '<ul class="nf-rows">';
    past.forEach(function (row) {
      /* AC-15. The rule's days are LABELLED, so nobody reads them as leave
         they asked for - and so the balance above and the history here add up
         to the same story. */
      var label = row.label
        ? '<span class="nf-row-sub">' + esc(row.label) + "</span>" : "";
      list += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(row.leave_type) + " · "
        + esc(row.from_date) + "</span>" + label + "</span>"
        + '<span class="nf-row-val">' + esc(num(row.days)) + "</span></li>";
    });
    return html + cardBox(esc(SAY.pastLeave), list + "</ul>", esc);
  }

  /* ── the Late rule ───────────────────────────────────────────────────────── */

  function ruleTab(data, ctx, SAY) {
    var esc = ctx.esc;
    var rule = data.rule || {};
    var html = "";

    if (!rule.covered) {
      /* AC-35. The tab is still here and says so. Showing zeros instead would
         read as "the rule is satisfied", which is a different thing entirely -
         and the one nobody would think to query. */
      html += cardBox(esc(SAY.rule),
                      '<p class="nf-card-note">' + esc(rule.note || "") + "</p>", esc);
    } else {
      var clauses = '<ul class="nf-rows">';
      (rule.clauses || []).forEach(function (clause) {
        /* One whole sentence per row, built on the SERVER from the rule
           record. Nothing here assembles a sentence and nothing here holds a
           number - which is why a tenant changing its threshold changes this
           screen and nobody has to remember to edit the copy (AC-12). */
        clauses += '<li class="nf-row"><span class="nf-row-main">'
          + '<span class="nf-row-title">' + esc(clause) + "</span></span></li>";
      });
      clauses += "</ul>";
      if (rule.accountable) {
        clauses += '<p class="nf-card-note">'
          + esc(SAY.accountable(rule.accountable)) + "</p>";
      }
      html += cardBox(esc(rule.rule_name || SAY.rule), clauses, esc);
    }

    return html + recordCard(data.record_this_year, esc, SAY);
  }

  function recordCard(record, esc, SAY) {
    if (!record) { return ""; }
    if (!record.months || !record.months.length) {
      return cardBox(esc(SAY.record),
                     '<p class="nf-card-note">' + esc(SAY.noRecord) + "</p>", esc);
    }
    /* The figure at the top is the server's `total_days`, and the months under
       it are the server's `months`, each carrying the weeks it is made of. The
       browser adds nothing up, so the total and the lists cannot disagree
       (AC-11, AC-13). */
    var html = '<p class="nf-hero-shift">' + esc(num(record.total_days)) + "</p>";
    html += '<ul class="nf-rows">';
    record.months.forEach(function (bucket) {
      var weeks = bucket.weeks.map(function (w) {
        return w.week_start + " – " + w.week_end;
      }).join(", ");
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(bucket.month) + "</span>"
        + '<span class="nf-row-sub">' + esc(weeks) + "</span></span>"
        + '<span class="nf-row-val">' + esc(num(bucket.days)) + "</span></li>";
    });
    html += "</ul>";
    if (record.capped) {
      /* Surbhi's standing rule: a list that was cut says so, rather than
         quietly disagreeing with the number above it. */
      html += '<p class="nf-card-note">' + esc(
        SAY.monthOf(record.weeks_listed, record.cap)) + "</p>";
    }
    return cardBox(esc(SAY.record), html, esc);
  }

  /* ── the day sheet ───────────────────────────────────────────────────────── */

  function openDay(date, data, ctx, opener) {
    var esc = ctx.esc, SAY = words(ctx);
    var day = null;
    (data.month.days || []).forEach(function (row) {
      if (row.date === date) { day = row; }
    });
    if (!day) { return; }

    var html = '<p class="nf-sheet-lead">' + esc(stateWords(day, SAY)) + "</p>";

    if (day.shift_starts) {
      html += '<p class="nf-card-note">' + esc(day.shift_starts) + " – "
        + esc(day.shift_ends || "") + "</p>";
    }
    if (day.in_time || day.out_time) {
      html += '<ul class="nf-rows"><li class="nf-row">'
        + '<span class="nf-row-main"><span class="nf-row-title">'
        + esc(day.in_time || "") + " – " + esc(day.out_time || "")
        + "</span></span></li></ul>";
    }

    /* AC-5. The grace row NAMES ITS SOURCE. Which record a figure came from is
       the difference between "the system says I was late" and "our shift
       forgives fifteen minutes and I was inside it". */
    html += '<p class="nf-card-note">' + esc(graceLine(day, data, SAY)) + "</p>";

    html += punchList(day, esc, SAY);

    if (day.request) {
      /* AC-9. Already asked about. No second Fix, and a plain line saying
         where the first one got to. */
      html += '<p class="nf-card-note">' + esc(requestLine(day, SAY)) + "</p>";
    } else if (data.month.can_request && canFix(day)) {
      html += '<div class="nf-sheet-acts">'
        + '<button type="button" class="nf-btn" id="nf-day-fix" data-day="'
        + esc(day.date) + '">' + esc(SAY.fix) + "</button>"
        + '<button type="button" class="nf-btn nf-btn-quiet" id="nf-day-leave"'
        + ' data-day="' + esc(day.date) + '">' + esc(SAY.onLeave) + "</button>"
        + "</div>";
    }

    ctx.openSheet(date, html, function (bodyNode) {
      var fix = bodyNode.querySelector("#nf-day-fix");
      if (fix) {
        fix.addEventListener("click", function () {
          openFix(day, data, ctx);
        });
      }
      var onLeave = bodyNode.querySelector("#nf-day-leave");
      if (onLeave) {
        onLeave.addEventListener("click", function () {
          /* AC-8. "I was on leave" is NOT a correction - it routes to the
             apply-leave flow for that date, and creates no Attendance
             Request. A day that was leave is not a day the attendance record
             got wrong. */
          ctx.closeSheet();
          ctx.go("time/leave?on=" + encodeURIComponent(day.date));
        });
      }
    }, opener);
  }

  function canFix(day) {
    var state = dayState(day);
    /* A holiday and a weekly off are not days to correct, and a day that is
       already present with nothing odd about it has nothing to fix. */
    return state === "absent" || state === "none" || state === "half"
      || day.missing_punch;
  }

  function graceLine(day, data, SAY) {
    if (!day.grace_mins) { return SAY.noGrace; }
    if (day.grace_source === "shift" && day.shift) {
      return SAY.graceShift(day.grace_mins, day.shift);
    }
    /* The organisation's own name, from the frame - never the word
       "organisation", and never a number written into this file. */
    var org = (document.body.getAttribute("data-tenant-name") || "").trim();
    return org ? SAY.graceOrg(day.grace_mins, org) : SAY.noGrace;
  }

  function punchList(day, esc, SAY) {
    var marks = day.punches || [];
    if (!marks.length) {
      return '<p class="nf-card-note">' + esc(SAY.noPunches) + "</p>";
    }
    var html = '<h3 class="nf-card-title">' + esc(SAY.punches) + "</h3>"
      + '<ul class="nf-rows">';
    marks.forEach(function (mark) {
      html += '<li class="nf-row"><span class="nf-row-main">'
        + '<span class="nf-row-title">' + esc(mark.at || "") + "</span>"
        + '<span class="nf-row-sub">' + esc(mark.log_type || "") + "</span>"
        + "</span></li>";
    });
    return html + "</ul>";
  }

  /* ── fixing a day ────────────────────────────────────────────────────────── */

  function openFix(day, data, ctx) {
    var esc = ctx.esc, SAY = words(ctx);
    /* AC-7. The range offered is the run of days AROUND this one that are in
       the same state and not already claimed - so a person who was marked
       absent on the 7th, 8th and 9th sends ONE request for the three, rather
       than three requests, or one request and two forgotten days. */
    var span = run(day, data.month.days);

    ctx.api(REASONS, {}).then(function (reasons) {
      var options = '<option value="">—</option>';
      (reasons || []).forEach(function (row) {
        options += '<option value="' + esc(row.value) + '">'
          + esc(row.label || row.value) + "</option>";
      });
      var html = '<p class="nf-sheet-lead">' + esc(span.from) + " – "
        + esc(span.to) + "</p>"
        /* Every input has a label, and the label is visible - not a
           placeholder, which disappears the moment somebody types. */
        + '<label class="nf-label" for="nf-fix-reason">' + esc(SAY.reason) + "</label>"
        + '<select class="nf-input" id="nf-fix-reason">' + options + "</select>"
        + '<label class="nf-label" for="nf-fix-note">' + esc(SAY.explain) + "</label>"
        + '<textarea class="nf-input" id="nf-fix-note" rows="3"></textarea>'
        + '<p class="nf-card-note" id="nf-fix-said" role="status"></p>'
        + '<div class="nf-sheet-acts">'
        + '<button type="button" class="nf-btn" id="nf-fix-send">'
        + esc(SAY.send) + "</button></div>";

      ctx.openSheet(SAY.fix, html, function (bodyNode) {
        bodyNode.querySelector("#nf-fix-send").addEventListener("click", function () {
          send(bodyNode, span, ctx, SAY, data);
        });
      });
    }).catch(function () {
      ctx.toast(SAY.cardFailed, "bad");
    });
  }

  function send(bodyNode, span, ctx, SAY, data) {
    var reason = bodyNode.querySelector("#nf-fix-reason").value;
    var said = bodyNode.querySelector("#nf-fix-said");
    var button = bodyNode.querySelector("#nf-fix-send");
    if (!reason) {
      /* AC-7: the reason is REQUIRED, and the server enforces it too. This
         says what to do next rather than "validation failed". */
      said.textContent = SAY.reasonNeeded;
      bodyNode.querySelector("#nf-fix-reason").focus();
      return;
    }
    button.disabled = true;
    ctx.api(RAISE, {
      from_date: span.from,
      to_date: span.to,
      reason: reason,
      explanation: bodyNode.querySelector("#nf-fix-note").value
    }).then(function () {
      ctx.closeSheet();
      ctx.toast(SAY.sent, "good");
      /* The counts are RE-READ from the server, never decremented here: a
         number worked out in two places is how a badge and a list come to
         disagree (Wave 1 AC-13). */
      ctx.reloadCounts();
      draw(ctx);
    }).catch(function (reason_) {
      button.disabled = false;
      said.textContent = refusalSentence(reason_) || SAY.cardFailed;
    });
  }

  /* The run of days around this one in the same state, stopping at anything
     already claimed. Used only to PRE-FILL the range; the server decides what
     it will accept. */
  function run(day, days) {
    var state = dayState(day);
    var index = -1, i;
    for (i = 0; i < days.length; i++) {
      if (days[i].date === day.date) { index = i; }
    }
    var from = index, to = index;
    while (from > 0 && sameRun(days[from - 1], state)) { from--; }
    while (to < days.length - 1 && sameRun(days[to + 1], state)) { to++; }
    return { from: days[from].date, to: days[to].date };
  }

  function sameRun(day, state) {
    return !!day && !day.request && !day.future && !day.before_joining
      && dayState(day) === state;
  }

  /* ── shared bits ─────────────────────────────────────────────────────────── */

  function cardBox(title, bodyHtml, esc) {
    return '<section class="nf-card"><h2 class="nf-card-title">' + title + "</h2>"
      + bodyHtml + "</section>";
  }

  function num(v) {
    if (v === null || v === undefined || v === "") { return "0"; }
    return String(Math.round(Number(v) * 100) / 100);
  }

  function shiftMonth(by) {
    var month = at.month + by;
    var year = at.year;
    if (month < 1) { month = 12; year--; }
    if (month > 12) { month = 1; year++; }
    at = { year: year, month: month };
  }

  function wire(data, ctx) {
    var root = document.getElementById("nf-screens") || document;

    Array.prototype.forEach.call(root.querySelectorAll(".nf-tab-btn"), function (node) {
      node.addEventListener("click", function () {
        tab = node.getAttribute("data-tab");
        /* Only the body is redrawn, and only from the payload already in
           hand. Switching a tab does not ask the server again: it is the same
           answer, and a second call would be a second age of the truth. */
        var SAY = words(ctx);
        document.getElementById("nf-time-body").innerHTML = body(data, ctx, SAY);
        Array.prototype.forEach.call(root.querySelectorAll(".nf-tab-btn"),
          function (other) {
            other.setAttribute("aria-selected",
              other.getAttribute("data-tab") === tab ? "true" : "false");
          });
        wireBody(data, ctx);
      });
    });

    var prev = document.getElementById("nf-cal-prev");
    var next = document.getElementById("nf-cal-next");
    if (prev) {
      prev.addEventListener("click", function () { shiftMonth(-1); draw(ctx); });
    }
    if (next) {
      next.addEventListener("click", function () { shiftMonth(1); draw(ctx); });
    }
    wireBody(data, ctx);
  }

  function wireBody(data, ctx) {
    var root = document.getElementById("nf-time-body");
    if (!root) { return; }
    Array.prototype.forEach.call(root.querySelectorAll("[data-day]"), function (node) {
      node.addEventListener("click", function () {
        openDay(node.getAttribute("data-day"), data, ctx, node);
      });
    });
  }

  if (window.NextFrame && window.NextFrame.panel) {
    window.NextFrame.panel("time", draw);
    window.NextFrame.panel("time/days", draw);
  }
  /* What the browser check drives, and what the DOM tests import. Deliberately
     small - the behaviour is exercised through these, not through internals. */
  window.NextTime = {
    draw: draw,
    build: build,
    dayState: dayState,
    stateWords: stateWords,
    openable: openable,
    run: run,
    graceLine: graceLine,
    setTab: function (name) { tab = name; },
    setMonth: function (y, m) { at = { year: y, month: m }; }
  };
})();
