/*
 * Turning a daily-use refusal code into the exact screen 01b §7.9/§7.12
 * describes, for the Attendance screen and the punch (US-39, US-40, and the
 * "on open" half of US-41). Slice 013, daily use.
 *
 * A SIBLING of join-screens.js, not an extension of it, on purpose: several
 * codes this app can receive at check-in - TOO_MANY_TRIES, SERVER_ERROR,
 * NO_INTERNET, APP_TOO_OLD - carry genuinely different words here than they do
 * at join (01b §7.12's check-in versions mention "photo kept" and a "For HR"
 * card the join versions do not), so one flat `code -> builder` table cannot
 * hold two right answers for one key. Making join-screens.js's table
 * context-aware would work too, but it is a bigger edit to a file another
 * session is reviewing right now than this ticket needs - see
 * 00-impact-analysis-daily-use.md §4.3 for the trade-off, written down before
 * this file was.
 *
 * Reuses (never copies) join-screens.js's date-formatting helpers via
 * `window.AlvoraaJoinScreens`, so the two files do not each grow their own
 * copy of "today at 9:01 am" logic.
 *
 * Pure and DOM-free, same contract as join-screens.js:
 *   screenFor(code, values, opts) -> {screen, heading, body, steps, buttons,
 *     retry, footerCode, card}
 * `card`, when present, names the extra facts a screen-for-HR card needs
 * (SERVER_ERROR, unknownCode) - checkin.js fills in the date and app version,
 * because this file has no clock or build number of its own to guess at.
 *
 * The app picks its screen from `code` alone, never the English sentence
 * Frappe also queues for its own logs (MA-30) - same rule as join-screens.js,
 * restated here because it is the one rule this whole file exists to keep.
 */
(function (root) {
  "use strict";

  function dateHelpers() {
    // In Node, join-screens.js is required directly; in the browser it hangs
    // its exports on window.AlvoraaJoinScreens. Either way, these two
    // functions are pure and read-only - never mutated, never re-implemented.
    if (typeof module !== "undefined" && module.exports) {
      return require("./join-screens.js");
    }
    return root.AlvoraaJoinScreens || {};
  }

  var STEPS_LOCATION_OFF = [
    "Swipe down from the top of your phone.",
    "Press Location so it turns on.",
    "Come back here and press Try again.",
  ];

  var STEPS_LOCATION_DENIED = [
    "Press Open phone settings.",
    "Press Permissions, then Location.",
    "Press \"Allow only while using the app\". Keep \"Use precise location\" on.",
  ];

  // Seconds -> a phrase a person reads out to nobody, not a countdown. Never
  // pretends to more precision than the server's own TTL has (rounds to the
  // nearest sensible unit) - this is the fix for the join-flow's own
  // TOO_MANY_TRIES bug (it always said "one minute"; see 05-review.md N-something),
  // not inherited into this table.
  function friendlyWait(seconds) {
    var n = Math.max(0, Math.round(Number(seconds) || 0));
    if (n <= 90) return "a minute";
    var minutes = Math.round(n / 60);
    if (minutes < 60) return minutes + " minutes";
    var hours = Math.round(minutes / 60);
    return hours === 1 ? "an hour" : hours + " hours";
  }

  // ── where and when (fix of 27 Sep 2026) ──────────────────────────────────

  // 740 -> "740 m"; 13216 -> "13.2 km"; 140400 -> "140 km" (01d §7.6).
  // Metres under 1 km, so a person near the gate reads a number they can
  // walk; one decimal up to 99.9 km, so 13 km is not written as "13216 m";
  // whole kilometres from 100 km, where a decimal says nothing.
  function formatDistance(metres) {
    var m = Math.max(0, Math.round(Number(metres) || 0));
    if (m < 1000) return m + " m";
    var km = Math.round(m / 100) / 10;
    if (km >= 100) return Math.round(m / 1000) + " km";
    return km.toFixed(1) + " km";
  }

  function strings() {
    if (typeof module !== "undefined" && module.exports) return require("./strings.js");
    return root.AlvoraaStrings;
  }

  // A radius of 0, or none at all, is Frappe HR's "no limit". Never "0 m".
  function hasRadius(radius) {
    return Math.round(Number(radius) || 0) > 0;
  }

  // The rule line on welcome and home. `workplace` is the server's
  // { name, radius_m } or null.
  function ruleLine(workplace) {
    if (workplace && workplace.name && hasRadius(workplace.radius_m)) {
      return "Check in within " + Math.round(Number(workplace.radius_m)) + " m of " + workplace.name;
    }
    return "Check in from anywhere";
  }

  // The short rule for the welcome list and Settings: "Within 200 m" or
  // "From anywhere" (radius 0 or none is Frappe HR's "no limit").
  function whereShort(workplace) {
    var t = strings().t;
    if (workplace && workplace.name && hasRadius(workplace.radius_m)) {
      return t("whereWithin", { radius: Math.round(Number(workplace.radius_m)) });
    }
    return t("whereAnywhere");
  }

  /*
   * Home's rule, inside the status card (01d §7.5). The server's own
   * check_in_rule (E-3) wins when it is sent; an older server's answer falls
   * back to the radius, the same rule ruleLine() follows.
   * Returns { kind: "radius" | "anywhere", line, note }.
   */
  function homeRule(data) {
    var t = strings().t;
    data = data || {};
    var wp = data.workplace;
    var radius = data.check_in_rule === "anywhere" ? false
      : (wp && wp.name && hasRadius(wp.radius_m));
    if (radius) {
      return { kind: "radius", line: ruleLine(wp), note: "" };
    }
    return { kind: "anywhere", line: t("ruleAnywhere"), note: t("ruleAnywhereNote") };
  }

  /*
   * The status card: where the person stands today, from today's punches.
   * Returns { kind: "idle" | "in" | "out", time } - FC-1: after a
   * check-out it is "out", never "not checked in yet".
   */
  function statusOf(rows) {
    var last = rows && rows.length ? rows[rows.length - 1] : null;
    if (!last) return { kind: "idle", time: null };
    return { kind: last.log_type === "IN" ? "in" : "out", time: last.time };
  }

  /*
   * The result list's location row (01d §7.6), from the server's measurement.
   * Returns { icon, headline, detail }. "At <workplace>" only when the
   * server measured the person inside its radius - never from the name alone.
   */
  function whereLines(loc, phoneAccuracy) {
    var t = strings().t;
    loc = loc || {};
    var acc = loc.accuracy_m !== undefined && loc.accuracy_m !== null ? loc.accuracy_m : phoneAccuracy;
    var hasAcc = acc !== undefined && acc !== null && acc !== "" && isFinite(Number(acc));
    var accuracy = hasAcc ? Math.round(Number(acc)) : null;
    var hasDistance = loc.distance_m !== undefined && loc.distance_m !== null && loc.distance_m !== "";
    if (loc.workplace && loc.within === true) {
      return {
        icon: "pin",
        headline: t("resultAt", { workplace: loc.workplace }),
        detail: hasAcc
          ? t("resultWithinDetail", { radius: Math.round(Number(loc.radius_m)), accuracy: accuracy })
          : t("whereWithin", { radius: Math.round(Number(loc.radius_m)) }),
      };
    }
    if (loc.workplace && hasDistance) {
      // "You may check in from anywhere" only when there really is no radius;
      // a radius the server did not enforce (within false) is not "anywhere".
      var anywhere = !hasRadius(loc.radius_m);
      var detail = anywhere
        ? (hasAcc ? t("resultAnywhereDetail", { accuracy: accuracy }) : t("resultAnywhereNoAccuracy"))
        : (hasAcc ? t("resultAccuracy", { accuracy: accuracy }) : "");
      return {
        icon: anywhere ? "globe" : "pin",
        headline: t("resultAbout", { distance: formatDistance(loc.distance_m), workplace: loc.workplace }),
        detail: detail,
      };
    }
    return {
      icon: "pin",
      headline: t("resultSaved"),
      detail: hasAcc ? t("resultAccuracy", { accuracy: accuracy }) : "",
    };
  }

  // The result card's "where you were" line. `loc` is field_checkin's
  // `location` answer: { workplace, radius_m, distance_m, within, accuracy_m }.
  // It names the workplace as where the person WAS only when the server
  // measured them inside its radius - never from the workplace's name alone.
  // `phoneAccuracy` is used when an older server sends no `location` at all.
  function whereLine(loc, phoneAccuracy) {
    loc = loc || {};
    var acc = loc.accuracy_m !== undefined && loc.accuracy_m !== null ? loc.accuracy_m : phoneAccuracy;
    var accText = (acc !== undefined && acc !== null && acc !== "" && isFinite(Number(acc)))
      ? " · accuracy " + Math.round(Number(acc)) + " m" : "";
    var hasDistance = loc.distance_m !== undefined && loc.distance_m !== null && loc.distance_m !== "";
    if (loc.workplace && loc.within === true) {
      return "At " + loc.workplace + " (within " + Math.round(Number(loc.radius_m)) + " m)" + accText;
    }
    if (loc.workplace && hasDistance) {
      return "About " + formatDistance(loc.distance_m) + " from " + loc.workplace + accText;
    }
    return "Location recorded" + accText;
  }

  // The phone's own wall-clock time with its offset from UTC, for
  // `captured_at`: "2026-09-27T14:05:09+05:30". The server turns it into the
  // site's time zone. (Before 0.2.1 the app sent UTC with no mark, and the
  // server read it as local time - 5 h 30 min early in India.)
  function localTimeWithOffset(date) {
    function pad(n) { return n < 10 ? "0" + n : String(n); }
    var offset = -date.getTimezoneOffset(); // minutes east of UTC
    var sign = offset >= 0 ? "+" : "-";
    var abs = Math.abs(offset);
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate())
      + "T" + pad(date.getHours()) + ":" + pad(date.getMinutes()) + ":" + pad(date.getSeconds())
      + sign + pad(Math.floor(abs / 60)) + ":" + pad(abs % 60);
  }

  function removeButton(company) {
    return "Remove " + (company || "this company") + " from this phone";
  }

  var SCREENS = {
    // ── the organisation's own switches, changed after this phone joined
    //    (US-41's "on open" half; AC-211: the secret is KEPT) ────────────────
    APP_OFF_FOR_FIELD: function (v, now, company) {
      return {
        screen: "appOff",
        heading: "The app is not switched on for field staff",
        body: (company || "Your company") + " has not turned on the app for field staff. "
          + "Keep marking attendance the way you do now. HR can tell you more.",
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },
    NOT_FIELD_ROLE: function (v, now, company) {
      return {
        screen: "notField",
        heading: "This app is not for your job yet",
        body: "In HR's records your job is " + (v.designation || "not a field role") + ". "
          + "For now the app is only for field staff, such as drivers and guards. "
          + "Keep marking attendance the usual way. If your job is wrong in the records, tell HR.",
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },
    FEATURE_OFF: function () {
      // The exact 008 web check-in page's body (www/field-checkin.html), not
      // the wording the join flow shipped with - see 05-review.md's N1
      // finding, which is why this file writes its own copy instead of
      // reusing join-screens.js's (already-wrong) one.
      return {
        screen: "featureOff",
        heading: "This app is not switched on for your company",
        body: "Field check-in is not part of your company's plan yet. Please tell HR.",
        steps: [],
        buttons: ["Try again"],
        retry: true,
      };
    },

    // ── the app build ────────────────────────────────────────────────────
    APP_TOO_OLD: function (v) {
      return {
        screen: "update",
        heading: "Update the app to keep marking attendance",
        body: "This version of Alvoraa is too old to work with your company any more. "
          + "Updating takes about a minute on Wi-Fi.",
        card: { onThisPhone: null, needed: v.min_version },
        steps: [],
        buttons: [], // build-type-specific (OPS-58): checkin.js decides the one button
        retry: false,
      };
    },

    // ── the phone (final states; D4: nothing here is reversible) ──────────
    DEVICE_BLOCKED: function (v, now, company) {
      return {
        screen: "blocked",
        heading: "This phone has been stopped",
        body: "HR has stopped this phone. It cannot mark attendance for you any more. "
          + "Please speak to HR.",
        card: { note: "Attendance you already marked is safe in your HR record. "
          + "If you have a new phone, HR can give you a new code." },
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },
    DEVICE_REPLACED: function (v, now, company) {
      var helpers = dateHelpers();
      var when = helpers.todayOrDateAt ? helpers.todayOrDateAt(v.replaced_at, now) : "";
      return {
        screen: "replaced",
        heading: "You joined on another phone",
        body: (when ? (when.charAt(0).toUpperCase() + when.slice(1)) : "Recently")
          + " you joined " + (company || "your company") + " on another phone. "
          + "Use that phone to mark attendance. If that was not you, tell HR today.",
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },
    // ALV-128 SEC-28: a phone that signed in with a login the employee record
    // no longer names. Same screen shape and button as "replaced": remove this
    // phone here, then sign in again.
    LOGIN_UNLINKED: function (v, now, company) {
      return {
        screen: "replaced",
        heading: "Please sign in again",
        body: "This phone was set up with a login that is no longer linked to your employee record. "
          + "Remove this phone, then sign in again. If you do not know why, speak to HR.",
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },
    EMPLOYEE_NOT_ACTIVE: function (v, now, company) {
      return {
        screen: "left",
        heading: "You cannot mark attendance here",
        body: "Your employee record at " + (company || "this company")
          + " is not active any more. If that is wrong, please speak to HR.",
        steps: [],
        buttons: [removeButton(company)],
        retry: false,
      };
    },

    // ── the punch (US-40; every one keeps the captured photo for Try again) ─
    LOCATION_MISSING: function () {
      // 008's own LOCATION_OFF wording (01b §7.12 tags this one "(008 wording)").
      return {
        screen: "locOff",
        heading: "Location is off",
        body: "We need to know where you are to mark your attendance. Turn on location, then try again.",
        steps: STEPS_LOCATION_OFF,
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    GPS_NOT_EXACT: function (v) {
      var accuracy = Math.round(Number(v.accuracy_m) || 0);
      var limit = Math.round(Number(v.limit_m) || 0);
      return {
        screen: "gpsVague",
        heading: "Your location is not exact enough",
        body: "Your phone can only place you within about " + accuracy + " m. It needs to be within "
          + limit + " m. Step outside or away from buildings, wait a few seconds, and press Try again.",
        card: { note: "Your photo is kept. You will not need to take it again." },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    OUTSIDE_WORKPLACE: function (v) {
      var site = v.site || "your workplace";
      var body = (v.distance_m !== undefined && v.distance_m !== null && v.distance_m !== "")
        ? "You are about " + formatDistance(v.distance_m) + " from " + site + ". You need to be within "
          + Math.round(Number(v.radius_m) || 0) + " m to check in. Walk closer and press Try again. "
          + "Nothing has been saved."
        // AC-208: the server's other sentence, when the distance cannot be measured.
        : "You are too far from " + site + " to check in.";
      return {
        screen: "outside",
        heading: "You are too far from work",
        body: body,
        card: { note: "Your photo is kept." },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    ALREADY_RECORDED: function (v, now) {
      var helpers = dateHelpers();
      var when = helpers.todayOrDateAt ? helpers.todayOrDateAt(v.time, now) : "";
      return {
        screen: "duplicate",
        heading: "That is already recorded",
        body: "You pressed the button twice. Your check-in "
          + (when || "just now") + " is saved. There is nothing more to do.",
        steps: [],
        buttons: ["Done"],
        retry: false,
      };
    },
    TOO_MANY_TRIES: function (v) {
      return {
        screen: "tooMany",
        heading: "Too many tries",
        body: "This phone tried many times in a short time. Wait " + friendlyWait(v.retry_after_s)
          + ", then press Try again.",
        card: { note: "Your photo is kept." },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    SERVER_ERROR: function () {
      return {
        screen: "serverError",
        heading: "Something went wrong",
        body: "Your attendance was not saved. Press Try again. If it keeps happening, "
          + "show this screen to HR.",
        card: { forHr: "SERVER_ERROR" },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    INVALID_REQUEST: function () {
      return {
        screen: "serverError",
        heading: "Something went wrong",
        body: "Your attendance was not saved. Press Try again. If it keeps happening, "
          + "show this screen to HR.",
        card: { forHr: "INVALID_REQUEST" },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },

    // ── client-made codes (§7.2 of the spec) - no server call ────────────
    LOCATION_DENIED: function () {
      return {
        screen: "locDenied",
        heading: "This app cannot see your location",
        body: "You said no to location. Attendance needs it. Allow location for Alvoraa, "
          + "then press Check In again.",
        steps: STEPS_LOCATION_DENIED,
        buttons: ["Open phone settings", "Go back"],
        retry: false,
      };
    },
    LOCATION_OFF: function () {
      return SCREENS.LOCATION_MISSING();
    },
    LOCATION_SLOW: function () {
      return SCREENS.LOCATION_MISSING();
    },
    NO_INTERNET: function () {
      return {
        screen: "noSignal",
        heading: "No internet",
        body: "Your attendance has not been saved yet. Move to a place with signal and press Try again.",
        card: { note: "Your photo is kept." },
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
  };

  var UNKNOWN_SCREEN = {
    screen: "unknownCode",
    heading: "Something went wrong",
    body: "Your attendance was not saved. This app may be out of date. Check for an update, then try again.",
    steps: [],
    buttons: ["Check for an update", "Try again"],
    retry: true,
  };

  /*
   * code     the server's code, or one of the client-made codes above
   * values   the refusal's `values` object (may be {})
   * opts     { now: Date, company: string } - both optional
   *
   * NOTICE_CHANGED, CONSENT_REQUIRED, NOT_SET_UP, DEVICE_PENDING and
   * DEVICE_REMOVED are deliberately NOT in this table - `gate-refusal.js`
   * (checkin.js's own dispatcher) intercepts all five before they ever reach
   * `screenFor()`: NOTICE_CHANGED and CONSENT_REQUIRED (05-review-daily-use.md,
   * M2) both need the full six-row notice shape, not this generic one -
   * CONSENT_REQUIRED's own values carry only `version`, so it is recovered by
   * fetching the full text via a deliberately-mismatched `acknowledge_notice`
   * call first; the other three mean "clear local state and go back to first
   * launch," not "show a problem screen." Calling `screenFor()` directly with
   * `CONSENT_REQUIRED` (as a caller outside the normal gate flow might) still
   * falls through to the honest unknown-code fallback below, never a blank
   * screen or a crash - this table's own safety net, not its design for the
   * code.
   */
  function screenFor(code, values, opts) {
    opts = opts || {};
    values = values || {};
    var build = SCREENS[code];
    var result = build ? build(values, opts.now, opts.company) : Object.assign({}, UNKNOWN_SCREEN);
    result.footerCode = code;
    return result;
  }

  var api = {
    screenFor: screenFor,
    friendlyWait: friendlyWait,
    formatDistance: formatDistance,
    ruleLine: ruleLine,
    whereShort: whereShort,
    homeRule: homeRule,
    statusOf: statusOf,
    whereLine: whereLine,
    whereLines: whereLines,
    localTimeWithOffset: localTimeWithOffset,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaCheckinScreens = api;
  }
})(typeof window !== "undefined" ? window : this);
