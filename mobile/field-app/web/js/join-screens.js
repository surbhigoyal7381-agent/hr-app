/*
 * Turning a server refusal code (or a code the app made itself) into the
 * exact screen 01b §7.12 describes: heading, body, numbered steps, buttons,
 * and "Code for HR: {CODE}" at the bottom (D11). Slice 013, US-37/US-38.
 *
 * Pure and DOM-free on purpose: this is the part of the join flow that is
 * actually worth proving with a test, the same reason field_app_errors.py on
 * the server is one small table rather than a refusal scattered through the
 * code. join.js only has to read what this returns and put it on the screen -
 * it should never itself decide what a code means.
 *
 * The app picks its screen from `code` ALONE, never the English sentence
 * Frappe also sends for its own logs (MA-30) - this file is that rule, made
 * concrete.
 */
(function (root) {
  "use strict";

  // ── small date/time formatting, no Intl dependency (works the same in
  //    Node's tests as it will in a WebView) ──────────────────────────────

  var WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];

  function pad2(n) { return n < 10 ? "0" + n : String(n); }

  function formatTime(date) {
    var h = date.getHours();
    var ampm = h < 12 ? "am" : "pm";
    var h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return h12 + ":" + pad2(date.getMinutes()) + " " + ampm;
  }

  function formatWeekdayDate(date) {
    return WEEKDAYS[date.getDay()] + " " + date.getDate() + " " + MONTHS[date.getMonth()];
  }

  function isSameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }

  function parseServerDate(value) {
    if (!value) return null;
    var d = new Date(String(value).replace(" ", "T"));
    return isNaN(d.getTime()) ? null : d;
  }

  // "on Thursday 24 September at 10:05 am" - qrExpired always uses this form.
  function onDateAt(value) {
    var d = parseServerDate(value);
    if (!d) return "";
    return "on " + formatWeekdayDate(d) + " at " + formatTime(d);
  }

  // "today at 9:01 am" or "on Thursday 24 September at 10:05 am" - qrUsed's
  // own branch (01b §7.12).
  function todayOrDateAt(value, now) {
    var d = parseServerDate(value);
    if (!d) return "";
    now = now || new Date();
    return isSameDay(d, now) ? "today at " + formatTime(d) : onDateAt(value);
  }

  // ── the table ────────────────────────────────────────────────────────────
  //
  // Each entry is a function of (values, now) so the two date-shaped ones can
  // read the clock; the rest ignore both arguments. Every screen ends with
  // footerCode - the app always renders "Code for HR: {footerCode}" (D11).

  var STEPS_ASK_HR = ["Ask HR for a new code.", "Scan the new code with this app."];

  var SCREENS = {
    QR_EXPIRED: function (v) {
      return {
        screen: "qrExpired",
        heading: "This code cannot be used any more",
        body: "It ran out " + onDateAt(v.expired_at) + ". HR's codes work for a limited time.",
        steps: STEPS_ASK_HR,
        buttons: ["Scan a new code", "Done"],
        retry: false,
      };
    },
    QR_USED: function (v, now) {
      return {
        screen: "qrUsed",
        heading: "This code cannot be used any more",
        body: "It was already used " + todayOrDateAt(v.used_at, now)
          + ". Each code works once. If that was not you, tell HR today.",
        steps: STEPS_ASK_HR,
        buttons: ["Scan a new code", "Done"],
        retry: false,
      };
    },
    QR_CANCELLED: function () {
      return {
        screen: "qrCancelled",
        heading: "This code cannot be used any more",
        body: "HR cancelled it. They may have made a newer one for you.",
        steps: STEPS_ASK_HR,
        buttons: ["Scan a new code", "Done"],
        retry: false,
      };
    },
    QR_NOT_RECOGNISED: function () {
      return {
        screen: "qrExpired", // same screen shape as the dead-code table (AC-193)
        heading: "This code cannot be used any more",
        body: "HR's codes work once, for a limited time.",
        steps: STEPS_ASK_HR,
        buttons: ["Scan a new code", "Done"],
        retry: false,
      };
    },
    APP_OFF_FOR_FIELD: function (v, now, company) {
      return {
        screen: "appOff",
        heading: "The app is not switched on for field staff",
        body: (company || "Your company") + " has not turned on the app for field staff. "
          + "Nothing was set up on this phone. Keep marking attendance the way you do now. "
          + "HR can tell you more.",
        steps: [],
        buttons: ["Done"],
        retry: false,
      };
    },
    NOT_FIELD_ROLE: function (v) {
      return {
        screen: "notField",
        heading: "This app is not for your job yet",
        body: "In HR's records your job is " + (v.designation || "not a field role") + ". "
          + "For now the app is only for field staff, such as drivers and guards. "
          + "Keep marking attendance the usual way. If your job is wrong in the records, tell HR.",
        steps: [],
        buttons: ["Done"],
        retry: false,
      };
    },
    FEATURE_OFF: function () {
      return {
        // Wording carried over from the 008 web check-in page (01b §7.12 cites
        // "(008 wording)" without repeating it here) - confirm byte-for-byte
        // against that page before this ships past a debug build.
        screen: "featureOff",
        heading: "This app is not switched on for your company",
        body: "Ask HR about the Alvoraa app for your company.",
        steps: [],
        buttons: ["Done"],
        retry: false,
      };
    },
    APP_TOO_OLD: function (v) {
      return {
        screen: "update",
        heading: "Update the app to keep marking attendance",
        body: "This version of Alvoraa is too old to work with your company any more.",
        values: { on_this_phone: null, needed: v.min_version },
        steps: [],
        buttons: [], // US-41's real update screen - not built this increment
        retry: false,
      };
    },
    SERVER_ERROR: function () {
      return {
        screen: "serverError",
        heading: "Something went wrong",
        body: "Your setup was not finished. Press Try again. If it keeps happening, show this screen to HR.",
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    TOO_MANY_TRIES: function () {
      return {
        screen: "tooMany",
        heading: "Too many tries",
        body: "This phone tried many times in a short time. Wait one minute, then press Try again.",
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    INVALID_REQUEST: function () {
      return {
        screen: "serverError",
        heading: "Something went wrong",
        body: "Your setup was not finished. Press Try again. If it keeps happening, show this screen to HR.",
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
    // Client-made codes (§7.2 of the spec) - no server call, no `values`.
    QR_NOT_ALVORAA: function () {
      return {
        screen: "notAlvoraa",
        heading: "This is not an Alvoraa code",
        body: "It may be a payment code or a website link. Scan the code HR gave you for this app. "
          + "Nothing was sent anywhere.",
        steps: [],
        buttons: ["Scan again", "Choose a picture instead"],
        retry: false,
      };
    },
    QR_NOT_FOUND: function () {
      return {
        screen: "pickNoQr",
        heading: "No QR code found in that picture",
        body: "Choose the picture HR sent you. A small code is fine, but it must not be cut off.",
        steps: [],
        buttons: ["Choose another picture", "Scan with the camera"],
        retry: false,
      };
    },
    CAMERA_DENIED: function () {
      return {
        screen: "camDenied",
        heading: "The camera is off for this app",
        body: "You said no to the camera. You can still join: choose the QR picture from your photos. "
          + "Or turn the camera on.",
        steps: ["Press Open phone settings.", "Press Permissions, then Camera.",
                "Press \"Allow only while using the app\", then come back."],
        buttons: ["Choose a picture instead", "Open phone settings"],
        retry: false,
      };
    },
    NO_INTERNET: function () {
      return {
        screen: "noSignalJoin",
        heading: "No internet",
        body: "The app needs the internet to check your code and finish setting up. "
          + "Nothing has been saved yet. Move to a place with signal and press Try again.",
        steps: [],
        buttons: ["Try again", "Go back"],
        retry: true,
      };
    },
  };

  // Any code the app does not have a row for, and any HTTP-level code with no
  // JSON at all (unlikely by the time this runs, since api.js already turns
  // those into TOO_MANY_TRIES/SERVER_ERROR/NO_INTERNET) - one honest fallback,
  // never a blank screen (§7.3 of the spec: "unknownCode").
  var UNKNOWN_SCREEN = {
    screen: "unknownCode",
    heading: "Something went wrong",
    body: "Your setup was not finished. This app may be out of date. Check for an update, then try again.",
    steps: [],
    buttons: ["Check for an update", "Try again"],
    retry: true,
  };

  /*
   * code     the server's code, or one of api.js's own client-made codes
   * values   the refusal's `values` object (may be {})
   * opts     { now: Date, company: string } - both optional, for the two
   *          date-shaped sentences and the company name in appOff
   *
   * Returns { screen, heading, body, steps, buttons, retry, footerCode }.
   * footerCode is always the CODE ITSELF, unknown or not (D11: "Code for HR"
   * is what the person reads out over the phone; it must be the real code
   * even when this app has no named screen for it yet).
   */
  function screenFor(code, values, opts) {
    opts = opts || {};
    values = values || {};
    var build = SCREENS[code];
    var result = build ? build(values, opts.now, opts.company) : Object.assign({}, UNKNOWN_SCREEN);
    result.footerCode = code;
    return result;
  }

  var api = { screenFor: screenFor, onDateAt: onDateAt, todayOrDateAt: todayOrDateAt };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaJoinScreens = api;
  }
})(typeof window !== "undefined" ? window : this);
