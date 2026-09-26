/*
 * The join flow, wired up for real: first launch through Welcome, the
 * dead-code screens, and "This is not me" (US-35, US-36, US-37, US-38).
 *
 * This file is the DOM-and-camera layer. It makes no decisions of its own -
 * every decision (what a server code means, whether a link is really an
 * Alvoraa code, how to shrink a photo, whether the storage is trustworthy)
 * lives in a small pure module this file only calls into:
 *   host-check.js, qr-decode.js, api.js, join-screens.js, device-secret.js.
 * Those are unit-tested; this file, being DOM- and camera-driven, is not -
 * it needs a real phone. See docs/slices/013-mobile-app/03-implementation-notes.md
 * §8 for exactly what is and is not proven here.
 *
 * Every value that came from the server is set with textContent, never
 * innerHTML (SEC-17, US-45) - a designation or company name typed by someone
 * in HR must never run as script on a driver's phone.
 */
(function () {
  "use strict";

  var BUILD_TYPE = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
  var app = document.getElementById("app");

  // ── tiny DOM helpers, all textContent - never innerHTML ───────────────────

  function el(id) { return document.getElementById(id); }

  function show(name) {
    var sections = app.querySelectorAll(".screen");
    for (var i = 0; i < sections.length; i++) {
      sections[i].hidden = sections[i].getAttribute("data-screen") !== name;
    }
    var target = app.querySelector('.screen[data-screen="' + name + '"]');
    if (target) target.focus && target.setAttribute("tabindex", "-1");
    state.screen = name;
  }

  function clearChildren(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function textEl(tag, text, className) {
    var node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  // ── app state - nothing here is ever written to disk (PRIV-7, AC-218) ────

  var state = {
    screen: null,
    origin: null,      // from the QR's own host - host-check.js sets this
    code: null,         // the 43-char code, memory only, never in storage or history
    lastAction: null,   // "check" | "join" | "refuse" - what "Try again" replays
    checkResult: null,  // E1's answer, kept for the notice/confirm screens
    stream: null,       // the open camera stream, if any
    rafId: null,
  };

  function stopCamera() {
    if (state.rafId) { cancelAnimationFrame(state.rafId); state.rafId = null; }
    if (state.stream) {
      state.stream.getTracks().forEach(function (t) { t.stop(); });
      state.stream = null;
    }
  }

  function resetJoinState() {
    stopCamera();
    state.origin = null;
    state.code = null;
    state.lastAction = null;
    state.checkResult = null;
  }

  // ── problem screens (01b §7.12) - one renderer for all of them ───────────
  //
  // join-screens.js decides the words; this table only says which button in
  // which position does what, by screen id. Position order matches the
  // `buttons` array join-screens.js returns for that code.

  var PROBLEM_ACTIONS = {
    qrExpired: ["scan-again", "done-to-first"],
    qrUsed: ["scan-again", "done-to-first"],
    qrCancelled: ["scan-again", "done-to-first"],
    notAlvoraa: ["open-scanner", "choose-picture"],
    pickNoQr: ["choose-picture", "open-scanner"],
    appOff: ["done-to-first"],
    notField: ["done-to-first"],
    featureOff: ["done-to-first"],
    // ALV-128: "signin-open" is signin.js's action - it opens the sign-in screen.
    codeJoinOff: ["signin-open", "done-to-first"],
    camDenied: ["choose-picture", "open-settings"],
    noSignalJoin: ["retry-last", "done-to-first"],
    serverError: ["retry-last", "done-to-first"],
    tooMany: ["retry-last", "done-to-first"],
    unknownCode: ["retry-last", "done-to-first"],
    update: [],
  };

  function showProblem(code, values, opts) {
    stopCamera();
    var info = window.AlvoraaJoinScreens.screenFor(code, values, opts || {});
    el("problem-heading").textContent = info.heading;
    el("problem-body").textContent = info.body;
    // 05-review-daily-use.md, M1: this file's own screens never set `card`,
    // but checkin.js's do, and the two share this one element - without this
    // line a card checkin.js showed earlier (e.g. "Your photo is kept.")
    // could still be sitting there under a brand new dead-code screen.
    window.AlvoraaProblemCard.render(el("problem-card"), textEl, info.card);

    var stepsList = el("problem-steps");
    clearChildren(stepsList);
    if (info.steps && info.steps.length) {
      info.steps.forEach(function (step) { stepsList.appendChild(textEl("li", step)); });
      stepsList.hidden = false;
    } else {
      stepsList.hidden = true;
    }

    var buttonsBox = el("problem-buttons");
    clearChildren(buttonsBox);
    var actions = PROBLEM_ACTIONS[info.screen] || [];
    (info.buttons || []).forEach(function (label, i) {
      var b = textEl("button", label);
      b.type = "button";
      b.setAttribute("data-action", actions[i] || "done-to-first");
      buttonsBox.appendChild(b);
    });

    el("problem-footer").textContent = "Code for HR: " + info.footerCode;
    show("problem");
  }

  // ── the scanner: open the camera, read frames, hand off to host-check ────

  function openScanner() {
    var video = el("scan-video");
    show("scan");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showProblem("SERVER_ERROR", {}); // this phone's WebView gives no camera at all
      return;
    }
    navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false,
    }).then(function (stream) {
      state.stream = stream;
      video.srcObject = stream;
      video.play();
      scanLoop();
    }).catch(function () {
      showProblem("CAMERA_DENIED", {});
    });
  }

  function scanLoop() {
    var video = el("scan-video");
    var canvas = el("scan-canvas");
    if (video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      var frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
      var result;
      try {
        result = window.AlvoraaQr.decode(frame);
      } catch (e) {
        result = null; // jsQR not loaded - treated as "nothing found this frame", not a crash
      }
      if (result && result.text) {
        handleScannedText(result.text);
        return; // stop the loop; handleScannedText moves the screen on
      }
    }
    state.rafId = requestAnimationFrame(scanLoop);
  }

  function handleScannedText(text) {
    stopCamera();
    var checked = window.AlvoraaHostCheck.checkEnrolLink(text, BUILD_TYPE);
    if (!checked.ok) {
      showProblem("QR_NOT_ALVORAA", {});
      return;
    }
    state.origin = checked.origin;
    state.code = checked.code;
    runCheck();
  }

  // ── "choose a picture" - a plain file input, the system's own picker ─────

  function choosePicture() {
    el("photo-picker").value = "";
    el("photo-picker").click();
  }

  function decodePickedFile(file) {
    show("checking");
    var img = new Image();
    var url = URL.createObjectURL(file);
    img.onload = function () {
      var canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.getContext("2d").drawImage(img, 0, 0);
      var frame = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      var result = null;
      try { result = window.AlvoraaQr.decode(frame); } catch (e) { result = null; }
      if (result && result.text) {
        handleScannedText(result.text);
      } else {
        showProblem("QR_NOT_FOUND", {});
      }
    };
    img.onerror = function () {
      URL.revokeObjectURL(url);
      showProblem("QR_NOT_FOUND", {});
    };
    img.src = url;
  }

  // ── E1: check the code (uses nothing) ─────────────────────────────────────

  function runCheck() {
    state.lastAction = "check";
    show("checking");
    window.AlvoraaApi.checkCode(state.origin, state.code, null).then(function (result) {
      if (result.ok) {
        state.checkResult = result.data;
        renderConfirm(result.data);
      } else {
        showProblem(result.code, result.values, {
          company: state.checkResult && state.checkResult.company,
        });
      }
    });
  }

  function renderConfirm(data) {
    var initial = (data.surname_initial || "").toUpperCase();
    el("confirm-initials").textContent = ((data.first_name || "?")[0] || "?").toUpperCase() + initial;
    el("confirm-name").textContent = data.first_name + (initial ? " " + initial + "." : "");
    el("confirm-designation").textContent = data.designation || "";
    el("confirm-company").textContent = data.company || "";
    show("confirm");
  }

  // ── E2: this is not me ────────────────────────────────────────────────────

  function refuseCode() {
    state.lastAction = "refuse";
    window.AlvoraaApi.refuseCode(state.origin, state.code).then(function (result) {
      if (result.ok) {
        show("notMeDone");
      } else if (result.code === "NO_INTERNET") {
        showProblem("NO_INTERNET", {});
      } else {
        // A dead or unknown code answers the same as E1 would (AC-62) -
        // there is nothing left to cancel; show the same dead-code screen.
        showProblem(result.code, result.values);
      }
    });
  }

  // ── the notice, and E3: agree and finish ──────────────────────────────────

  function renderNotice(data) {
    var initial = (data.surname_initial || "").toUpperCase();
    el("notice-topbar").textContent = [data.company, (data.first_name || "") + (initial ? " " + initial + "." : ""), data.designation]
      .filter(Boolean).join(" · ");
    el("notice-intro").textContent = (data.company || "Your company")
      + " asks you to read this. It says what the app records about you.";

    var rowsBox = el("notice-rows");
    clearChildren(rowsBox);
    var notice = data.notice || {};
    (notice.rows || []).forEach(function (row) {
      rowsBox.appendChild(textEl("h3", row.heading));
      rowsBox.appendChild(textEl("p", row.body));
    });

    el("notice-agree-words").textContent = notice.agree || "I have read this and I understand.";
    el("notice-tick").checked = false;
    el("notice-tick-error").hidden = true;
    show("notice");
  }

  function agreeAndFinish() {
    if (!el("notice-tick").checked) {
      el("notice-tick-error").hidden = false;
      el("notice-tick").focus();
      return;
    }
    el("notice-tick-error").hidden = true;

    state.lastAction = "join";
    show("joining");
    var notice = (state.checkResult && state.checkResult.notice) || {};
    window.AlvoraaApi.joinWithCode(state.origin, {
      code: state.code,
      notice_version: notice.version,
      device_label: "", // AC-220: model name only, added when the app reads Device.getInfo() for real
      platform: "android",
    }).then(function (result) {
      if (!result.ok) {
        if (result.code === "NOTICE_CHANGED") {
          // Minimal, in-place handling (US-42's full "read it again" screen
          // is not built this increment): refresh the SAME notice screen with
          // the server's new rows and ask the person to tick and agree again.
          // NOTE: NOTICE_CHANGED's `values` (version, rows, retention_days,
          // what_changed) do not include `agree` - field_app_errors.py's own
          // allow-list for this code does not carry it. renderNotice() falls
          // back to today's one real version's exact wording, which is
          // correct now but would go stale if a future notice version ever
          // changed the tick-box words - worth a small server-side addition
          // if that ever happens, not a client-side guess.
          state.checkResult = Object.assign({}, state.checkResult, { notice: result.values });
          renderNotice(state.checkResult);
          return;
        }
        showProblem(result.code, result.values, {
          company: state.checkResult && state.checkResult.company,
        });
        return;
      }
      window.AlvoraaDeviceSecret.save(result.data.token)
        // US-39/43 (daily-use build): the secret alone is not enough to run
        // the app after a restart - E4/E5/E6/E9 also need to know WHICH
        // tenant to call, and Settings' "What this app records" (AC-215)
        // needs the notice's own words saved somewhere it can read them with
        // no call. Both are written here, in the same order as the secret
        // (server confirmed first, write after) - see
        // 00-impact-analysis-daily-use.md §4.1/§4.4.1.
        .then(function () { return window.AlvoraaDeviceSecret.saveOrigin(state.origin); })
        .then(function () {
          window.AlvoraaNoticeCache.save({
            version: notice.version,
            rows: notice.rows || [],
            agree: notice.agree,
            retentionDays: notice.retention_days,
            // The phone's own clock, for display only (Settings shows "You
            // agreed on..."). The record that actually matters for a rights
            // request is server-side (record_acknowledgement); this is not it.
            agreedAt: new Date().toISOString().replace("T", " ").slice(0, 19),
          });
          renderWelcome(result.data);
        }).catch(function () {
        // The server has already joined this phone; the secret or the origin
        // failed to save. Nothing safe to do but say so plainly - this is
        // exactly the device-round-trip question the spike could not answer
        // without a real phone (03-implementation-notes.md §7.4/§7.5).
        showProblem("SERVER_ERROR", {});
      });
    });
  }

  function renderWelcome(data) {
    el("welcome-heading").textContent = "Welcome, " + data.first_name + ". This phone is set up.";
    var card = el("welcome-card");
    clearChildren(card);
    card.appendChild(textEl("p", "Company · " + (data.company || "")));
    if (data.workplace && data.workplace.name) {
      card.appendChild(textEl("p", "Your workplace · " + data.workplace.name));
    }
    // A radius of 0 or none means no limit - never "Check in within 0 m" (27 Sep 2026).
    card.appendChild(textEl("p", window.AlvoraaCheckinScreens.ruleLine(data.workplace)));
    show("welcome");
  }

  // ── retrying whatever the last server call was ────────────────────────────

  function retryLast() {
    if (state.lastAction === "check") runCheck();
    else if (state.lastAction === "join") agreeAndFinish();
    else if (state.lastAction === "refuse") refuseCode();
    else show("first");
  }

  // ── wiring: one delegated click listener for every data-action ───────────

  var ACTIONS = {
    "scan-pressed": openScanner, // AC-182: camExplain only shown once permission has never been asked;
                                  // Permissions API support is inconsistent across WebViews, so this
                                  // increment always explains first (safe default) - see notes §8.
    "open-scanner": openScanner,
    "choose-picture": choosePicture,
    "cancel-scan": function () { stopCamera(); show("first"); },
    "confirm-yes": function () { renderNotice(state.checkResult); },
    "confirm-not-me": function () { show("notMe"); },
    "not-me-go-back": function () { show("confirm"); },
    "cancel-code": refuseCode,
    "done-to-first": function () { resetJoinState(); show("first"); },
    "notice-back": function () { show("confirm"); },
    "agree-and-finish": agreeAndFinish,
    // US-39: the Attendance screen is checkin.js's, not this file's. Both
    // buttons hand off to it - "Check In" starts the punch straight away,
    // "Not now" just shows the Attendance screen unchecked-in (checkin.js's
    // own loadStatus() decides which, from the server's actual state, so
    // this file does not need to guess).
    "welcome-check-in": function () { window.AlvoraaCheckin.start({ autoPunch: true }); },
    "welcome-not-now": function () { window.AlvoraaCheckin.start(); },
    "scan-again": function () { resetJoinState(); openScanner(); },
    "retry-last": retryLast,
    // No vetted plugin yet opens Android's own per-app settings page (that
    // needs its own native-plugin decision, not made in this increment - see
    // 03-implementation-notes.md §8). Best effort: some WebViews re-show the
    // permission prompt on a fresh getUserMedia() call unless the person
    // chose "don't ask again"; if not, "Choose a picture instead" still works.
    "open-settings": openScanner,
  };

  app.addEventListener("click", function (event) {
    var target = event.target.closest && event.target.closest("[data-action]");
    if (!target) return;
    var action = ACTIONS[target.getAttribute("data-action")];
    if (action) action();
  });

  el("photo-picker").addEventListener("change", function (event) {
    var file = event.target.files && event.target.files[0];
    if (file) decodePickedFile(file);
  });

  // First launch always shows camExplain before the scanner - see the
  // "scan-pressed" comment above for why this increment does not try to
  // detect an already-granted permission.
  ACTIONS["scan-pressed"] = function () { show("camExplain"); };

  // US-39/43 (daily-use build): this file no longer decides on its own that
  // a fresh page load means "show first launch" - a joined phone opening the
  // app should go straight to the Attendance screen instead. That single
  // decision (does this phone already have a secret?) now lives in main.js,
  // which calls this exported start() only when it decides the join flow is
  // the right one to show. Nothing else in this file changed.
  //
  // ALV-128: a phone that is not set up now starts on the sign-in screen
  // (signin.js), which leads with email and password. `start()` is still the
  // one door main.js and checkin.js call; `startQr()` is this file's own QR
  // screen, reached from "I have a joining code". Nothing else here changed.
  window.AlvoraaJoin = {
    start: function () {
      resetJoinState();
      if (window.AlvoraaSignin) window.AlvoraaSignin.start();
      else show("first");
    },
    startQr: function () { resetJoinState(); show("first"); },
  };
})();
