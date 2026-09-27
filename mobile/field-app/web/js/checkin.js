/*
 * The daily-use flow, wired up for real: the Attendance screen and the punch
 * (US-39), the punch's own problem screens (US-40), the gate the app runs
 * through on every open (the "on open" half of US-41), the changed-notice
 * screen (US-42), and Settings (US-43). Slice 013, daily use. Restyled on
 * Material 3 and given "Stop agreeing to the notice" in ALV-133.
 *
 * Same division of labour as join.js: this file is the DOM/camera/geolocation
 * layer and makes no decisions of its own about what a code means - that
 * lives in checkin-screens.js (pure, unit-tested). This file, being DOM- and
 * camera-driven, is not unit-tested - it needs a real phone, same honest limit
 * join.js already states. See docs/slices/013-mobile-app/03-implementation-notes.md
 * for exactly what is and is not proven here.
 *
 * Every server-sent value is set with textContent, never innerHTML (SEC-17,
 * US-45) - the same rule join.js already follows, restated here because it is
 * the one rule this file must never break.
 */
(function () {
  "use strict";

  var app = document.getElementById("app");
  var ui = window.AlvoraaUi;
  var t = window.AlvoraaStrings.t;
  var screens = window.AlvoraaCheckinScreens;

  function el(id) { return document.getElementById(id); }

  function show(name) {
    ui.closeAllOverlays();
    var sections = app.querySelectorAll(".screen");
    for (var i = 0; i < sections.length; i++) {
      sections[i].hidden = sections[i].getAttribute("data-screen") !== name;
    }
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

  // ── a tiny, local, non-sensitive flag: has this phone shown locExplain
  //    before? (AC-198: only the FIRST check-in ever shows it.) Wrapped the
  //    same fail-soft way notice-cache.js wraps localStorage.
  var LOCATION_EXPLAINED_KEY = "alvoraa_location_explained";
  function hasSeenLocationExplain() {
    try { return localStorage.getItem(LOCATION_EXPLAINED_KEY) === "1"; } catch (e) { return false; }
  }
  function markLocationExplainSeen() {
    try { localStorage.setItem(LOCATION_EXPLAINED_KEY, "1"); } catch (e) { /* fail soft */ }
  }

  // ── state - nothing here is written to disk except through the modules
  //    that are meant to (device-secret.js, notice-cache.js, theme.js) ──────
  var state = {
    origin: null,
    secret: null,
    status: null,            // the last field_status answer, for Settings and Records
    company: null,
    workplaceName: null,
    radiusM: null,
    checkedIn: false,
    minVersion: null,
    lastAction: null,        // "status" | "punch" | "remove" | "notice" | "withdraw"
    pendingLogType: null,    // "IN" or "OUT" - what Try again resends
    photoDataUrl: null,      // kept across Try again (AC-205)
    photoTakenAt: null,      // the phone's clock when the photo was taken
    skipPhoto: false,        // the person chose "Check in without a photo"
    camera: null,            // camera.js's instance, made on first use
    cameraReopen: false,     // the preview was stopped because the app was paused
    noticeAgainValues: null, // the six rows to re-render on noticeAgain
    removeLocal: false,      // the sheet removes this phone here only (a final state)
    slowTimer: null,
  };

  function stopCamera() {
    if (state.camera) state.camera.cancel();
  }

  function resetPunchState() {
    state.photoDataUrl = null;
    state.photoTakenAt = null;
    state.skipPhoto = false;
    state.pendingLogType = null;
  }

  // ── the shared problem screen (reuses index.html's #problem, exactly as
  //    join.js's own showProblem does - only one of the two ever runs) ──────

  var PROBLEM_ACTIONS = {
    appOff: ["checkin-open-leave-confirm-from-gate"],
    notField: ["checkin-open-leave-confirm-from-gate"],
    featureOff: ["checkin-retry-status"],
    blocked: ["checkin-local-remove"],
    replaced: ["checkin-local-remove"],
    left: ["checkin-local-remove"],
    locOff: ["checkin-retry-last", "checkin-go-home"],
    locDenied: ["checkin-open-os-settings", "checkin-go-home"],
    gpsVague: ["checkin-retry-last", "checkin-go-home"],
    outside: ["checkin-retry-last", "checkin-go-home"],
    noSignal: ["checkin-retry-last", "checkin-go-home"],
    tooMany: ["checkin-retry-last", "checkin-go-home"],
    serverError: ["checkin-retry-last", "checkin-go-home"],
    duplicate: ["checkin-go-home"],
    unknownCode: ["checkin-check-update", "checkin-retry-last"],
    update: [], // its one line is built below, by build type
  };

  // A "Remove ... from this phone" button is not the main action: it is
  // tonal, never the brand colour (01d §7.7).
  var TONAL_FIRST = { appOff: true, notField: true, blocked: true, replaced: true, left: true };

  // 05-review-daily-use.md, M1: the card is rendered through the SAME shared
  // helper join.js uses (problem-card.js), so there is one place, not two,
  // that decides what #problem-card shows - and every call clears it first.
  function renderCard(info) {
    var card = Object.assign({}, info.card);
    if (info.card && info.card.onThisPhone !== undefined) {
      card.appVersion = window.AlvoraaVersion ? window.AlvoraaVersion.APP_VERSION : "";
    }
    if (info.card && info.card.forHr) {
      card.when = new Date().toString();
      card.appVersion = window.AlvoraaVersion ? window.AlvoraaVersion.APP_VERSION : "";
    }
    window.AlvoraaProblemCard.render(el("problem-card"), textEl, info.card ? card : undefined);
    // The blocked screen's "you are safe" note is good news: green (01d §7.7).
    el("problem-card").className = "card " + (info.screen === "blocked" ? "success" : "info");
  }

  function problemBar() {
    var known = !!state.company;
    el("problem-alv-mark").hidden = known;
    el("problem-mark").hidden = !known;
    el("problem-mark").textContent = ui.initials(state.company);
    el("problem-bar-title").textContent = known ? state.company : "Alvoraa Attendance";
  }

  function showProblem(code, values, opts) {
    stopCamera();
    clearSlowTimer();
    // Remembered so "Keep it" on the Remove sheet opened FROM one of these
    // gate screens simply closes the sheet over the exact same screen.
    state.lastGateCode = code;
    state.lastGateValues = values;
    var info = screens.screenFor(code, values, Object.assign({ company: state.company }, opts || {}));
    problemBar();
    var look = ui.problemLook(info.screen);
    ui.setBubble(el("problem-bubble"), look.icon, look.tone);
    el("problem-heading").textContent = info.heading;
    el("problem-body").textContent = info.body;
    renderCard(info);

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

    if (info.screen === "update") {
      // OPS-58: no Play listing or tester link exists yet to embed, and the
      // bundle may hold no outside address (SEC-16/OPS-22), so this build
      // gives plain instructions instead of a button - a declared gap.
      var buildType = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
      var guidance = buildType === "debug" ? "Ask the developer."
        : buildType === "pilot" ? "Ask HR for the update link you were sent."
        : "Open the Play Store and search for Alvoraa, or ask HR.";
      buttonsBox.appendChild(textEl("p", guidance, "t-body-m muted"));
    } else {
      var actions = PROBLEM_ACTIONS[info.screen] || [];
      (info.buttons || []).forEach(function (btnLabel, i) {
        var kind = i === 0 ? (TONAL_FIRST[info.screen] ? "tonal" : "filled") : "outlined";
        var button = textEl("button", btnLabel, "btn block " + kind);
        button.type = "button";
        button.setAttribute("data-action", actions[i] || "checkin-go-home");
        buttonsBox.appendChild(button);
      });
    }

    el("problem-footer").textContent = t("codeForHr", { code: info.footerCode });
    show("problem");
  }

  function retryLast() {
    if (state.lastAction === "status") loadStatus();
    else if (state.lastAction === "punch") doPunch(state.pendingLogType);
    else if (state.lastAction === "remove") doRemove();
    else if (state.lastAction === "notice") agreeToNoticeAgain();
    else if (state.lastAction === "withdraw") doWithdraw();
    else show("home");
  }

  // ── boot: does this phone have a secret? then call field_status (E4) ────

  /*
   * opts.autoPunch: true when the join flow's own "Check In" button (01b's
   * `welcome` screen) sent us here - welcome -> Check In -> locExplain ->
   * punching directly, not via home first. "Not now" calls start() with no
   * options, landing on home, which is also what a normal app open does.
   */
  function start(opts) {
    state.autoPunch = !!(opts && opts.autoPunch);
    Promise.all([
      window.AlvoraaDeviceSecret.load(),
      window.AlvoraaDeviceSecret.loadOrigin(),
    ]).then(function (results) {
      state.secret = results[0];
      state.origin = results[1];
      if (!state.secret || !state.origin) {
        // A half-set-up phone (one key present, not the other) is not set up
        // at all from the person's point of view - back to first launch.
        window.AlvoraaJoin.start();
        return;
      }
      // The colour this phone last wore, so the loading screen is already
      // the company's; field_status then confirms it (E-1).
      window.AlvoraaTheme.applyRemembered();
      state.company = state.company || rememberedCompanyName();
      loadStatus();
    });
  }

  // The company's name, kept on the phone so a refusal on open (blocked,
  // replaced, left) can still say "Remove PP Jewellers from this phone" and
  // show the company's mark. A company name is not personal data.
  var COMPANY_NAME_KEY = "alvoraa_company_name";
  function rememberCompanyName(name) {
    try { if (name) localStorage.setItem(COMPANY_NAME_KEY, name); } catch (e) { /* fail soft */ }
  }
  function rememberedCompanyName() {
    try { return localStorage.getItem(COMPANY_NAME_KEY) || null; } catch (e) { return null; }
  }

  function forgetPhoneLocally() {
    stopCamera();
    return window.AlvoraaDeviceSecret.clear().then(function () {
      window.AlvoraaNoticeCache.clear();
      window.AlvoraaTheme.reset();
      try { localStorage.removeItem(COMPANY_NAME_KEY); } catch (e) { /* nothing kept */ }
      state.company = null;
      state.status = null;
    });
  }

  // ALV-128, 26 Sep 2026: the login's password changed, so the server signed
  // this phone out. Forget the stored secret (the server has retired it
  // anyway) and open the sign-in screen with the company code kept. The old
  // secret goes to the sign-in in memory only, so the server can tell it is
  // the same phone and sends no "new phone" email.
  function signInAgain() {
    var oldSecret = state.secret;
    var oldOrigin = state.origin;
    forgetPhoneLocally().then(function () {
      state.secret = null;
      state.origin = null;
      window.AlvoraaSignin.start({
        reason: "PASSWORD_CHANGED_SIGN_IN_AGAIN",
        previousToken: oldSecret,
        origin: oldOrigin,
      });
    });
  }

  function isSignedOut(code) {
    return window.AlvoraaGateRefusal.planForGateRefusal(code, {}).action === "signInAgain";
  }

  function loadStatus() {
    state.lastAction = "status";
    // A skeleton at once (nfr-budget §2): the Check In button waits for the
    // real status, so it can never say the wrong thing.
    show("homeLoading");
    window.AlvoraaApi.fieldStatus(state.origin, state.secret).then(function (result) {
      if (result.ok) {
        renderHome(result.data);
        return;
      }
      handleGateRefusal(result.code, result.values);
    });
  }

  // The full notice words for a phone in "Consent not given": its own refusal
  // carries only the version (05-review-daily-use.md, M2), so the rows are
  // fetched by sending acknowledge_notice a version it cannot match - the
  // server refuses with NOTICE_CHANGED and the rows attached. No new endpoint.
  function probeNotice(mode) {
    state.lastAction = "status";
    window.AlvoraaApi.acknowledgeNotice(state.origin, state.secret, "").then(function (result) {
      var probePlan = window.AlvoraaGateRefusal.planForConsentRequiredProbe(result);
      if (probePlan.action === "noticeAgain") {
        state.noticeAgainValues = probePlan.values;
        renderNoticeAgain(probePlan.values, mode);
      } else if (probePlan.action === "reloadStatus") {
        loadStatus();
      } else if (isSignedOut(probePlan.code)) {
        signInAgain();
      } else {
        showProblem(probePlan.code, probePlan.values);
      }
    });
  }

  function handleGateRefusal(code, values) {
    var plan = window.AlvoraaGateRefusal.planForGateRefusal(code, values);
    if (plan.action === "forgetAndFirst") {
      forgetPhoneLocally().then(function () {
        window.AlvoraaJoin.start();
      });
      return;
    }
    if (plan.action === "signInAgain") {
      signInAgain();
      return;
    }
    if (plan.action === "noticeAgain") {
      state.noticeAgainValues = plan.values;
      renderNoticeAgain(plan.values);
      return;
    }
    if (plan.action === "probeConsentRequired") {
      probeNotice();
      return;
    }
    showProblem(plan.code, plan.values);
  }

  // ── the Attendance screen (US-39, AC-197; 01d §7.5) ─────────────────────

  function renderHome(data) {
    state.status = data;
    state.company = data.company || "";
    rememberCompanyName(state.company);
    state.checkedIn = !!data.checked_in;
    state.workplaceName = data.workplace && data.workplace.name;
    state.radiusM = data.workplace && data.workplace.radius_m;
    state.minVersion = data.min_version;
    window.AlvoraaTheme.applyBrand(data.brand_colour);

    ui.setBrandBar(el("home-mark"), el("home-company"), el("home-person"), state.company,
      data.employee_name || data.first_name || "");

    var now = new Date();
    el("home-greeting").textContent = t(window.AlvoraaTheme.greetingKey(now),
      { name: data.first_name || "" });
    el("home-date").textContent = ui.dayDate(now);

    var rows = data.todays_checkins || [];
    var status = screens.statusOf(rows);
    var card = el("home-status");
    card.className = "status " + status.kind;
    if (status.kind === "in") {
      ui.setIcon(el("home-status-icon"), "checkCircle");
      el("home-status-label").textContent = t("statusIn");
      el("home-status-text").textContent = t("statusInSince", { time: clockOnly(status.time) });
    } else if (status.kind === "out") {
      // FC-1: an "out" state never claims "not checked in yet today".
      ui.setIcon(el("home-status-icon"), "logout");
      el("home-status-label").textContent = t("statusOut");
      el("home-status-text").textContent = t("statusOutAt", { time: clockOnly(status.time) });
    } else {
      ui.setIcon(el("home-status-icon"), "clock");
      el("home-status-label").textContent = t("statusToday");
      el("home-status-text").textContent = t("statusNotYet");
    }

    // Always shown since 27 Sep 2026: a radius of 0 or none is "Check in from
    // anywhere", never hidden and never "0 m".
    var rule = screens.homeRule(data);
    ui.setIcon(el("home-rule-icon"), rule.kind === "radius" ? "pin" : "globe", "s20");
    el("home-rule").textContent = rule.line;
    el("home-rule").className = rule.kind === "anywhere" ? "rule-strong" : "";
    el("home-rule-note").textContent = rule.note;
    el("home-rule-note").hidden = !rule.note;

    var button = el("home-punch-button");
    el("home-punch-label").textContent = state.checkedIn ? t("checkOut") : t("checkIn");
    ui.setIcon(el("home-punch-icon"), state.checkedIn ? "logout" : "login");
    // D-M3-2: one brand colour for both; the state is in the status card.
    button.className = "btn filled block large";

    var list = el("home-punch-list");
    clearChildren(list);
    if (!rows.length) {
      list.appendChild(textEl("p", t("noPunchesYet"), "t-body-m muted"));
    } else {
      var ul = document.createElement("ul");
      ul.className = "list card outlined flush";
      ui.fillList(ul, rows.map(function (row) {
        var isIn = row.log_type === "IN";
        return { lead: isIn ? "login" : "logout", hl: isIn ? t("punchIn") : t("punchOut"),
                 trail: clockOnly(row.time) };
      }));
      list.appendChild(ul);
    }

    el("home-camera-off").hidden = state.cameraAvailable !== false;

    if (state.autoPunch) {
      // 01b §6: welcome's own "Check In" goes straight into the punch. Only
      // ever fires once per start() call.
      state.autoPunch = false;
      pressPunch();
      return;
    }
    show("home");
  }

  function clockOnly(value) {
    var d = new Date(String(value).replace(" ", "T"));
    if (isNaN(d.getTime())) return String(value || "");
    return ui.clock(d);
  }

  // ── Check In / Check Out ─────────────────────────────────────────────────

  function pressPunch() {
    // A fresh press always takes a fresh photo. Only "Try again" on a problem
    // screen resends the one already taken (AC-205, retryLast -> doPunch).
    resetPunchState();
    var logType = state.checkedIn ? "OUT" : "IN";
    if (logType === "IN" && !hasSeenLocationExplain()) {
      state.pendingLogType = logType;
      show("locExplain");
      return;
    }
    doPunch(logType);
  }

  function continueFromLocExplain() {
    markLocationExplainSeen();
    doPunch(state.pendingLogType);
  }

  // ── the camera screen (fix of 27 Sep 2026; restyled in ALV-133) ─────────
  //
  // The person sees the preview, presses "Take photo", sees the still, and
  // chooses "Use photo" or "Retake". "Cancel" goes home and sends nothing.
  // camera.js holds the steps and stops the stream on every way out.

  function cameraView(which) {
    // which: "opening" | "live" | "still" | "denied" | "unavailable"
    var live = which === "live" || which === "opening";
    var failed = which === "denied" || which === "unavailable";
    el("camera-video").hidden = !live;
    el("camera-still").hidden = which !== "still";
    el("camera-take").hidden = !live;
    el("camera-take-caption").hidden = !live;
    el("camera-take").disabled = which !== "live";
    el("camera-use").hidden = which !== "still";
    el("camera-retake").hidden = which !== "still";
    el("camera-try-again").hidden = !failed;
    el("camera-no-photo").hidden = !failed;
    el("camera-who-sees").hidden = failed;
    var message = el("camera-message");
    if (which === "denied") {
      message.textContent = "The camera is off for this app. To take your photo, allow Camera for "
        + "Alvoraa in your phone's settings, then press Try the camera again. "
        + "Or check in without a photo - your attendance still counts.";
      message.hidden = false;
    } else if (which === "unavailable") {
      message.textContent = "The camera could not be opened. Press Try the camera again. "
        + "Or check in without a photo - your attendance still counts.";
      message.hidden = false;
    } else {
      message.textContent = "";
      message.hidden = true;
    }
    var status = el("camera-status");
    if (which === "opening") status.textContent = "Opening the camera";
    else if (which === "live") status.textContent = t("cameraHint");
    else if (which === "still") status.textContent = "Is your face clear?";
    else status.textContent = "";
    status.hidden = !status.textContent;
  }

  function camera() {
    if (!state.camera) {
      var devices = navigator.mediaDevices;
      state.camera = window.AlvoraaCamera.createCamera({
        getUserMedia: devices && devices.getUserMedia ? devices.getUserMedia.bind(devices) : null,
        video: el("camera-video"),
        shrink: window.AlvoraaPhoto.shrinkToJpeg,
      });
    }
    return state.camera;
  }

  function openCameraScreen() {
    el("camera-heading").textContent = state.pendingLogType === "OUT"
      ? "Take your photo to check out" : "Take your photo to check in";
    show("camera");
    cameraView("opening");
    camera().open().then(function (s) {
      if (currentScreen() !== "camera") {
        camera().cancel(); // the person left while it opened: no camera left on
        return;
      }
      if (s === "live" && !camera().ready()) {
        // "Take photo" works from the first real frame, not before.
        el("camera-video").addEventListener("loadeddata", function () {
          if (camera().state() === "live" && currentScreen() === "camera") cameraView("live");
        }, { once: true });
        return;
      }
      cameraView(s);
    });
  }

  function takePhoto() {
    if (!camera().take()) return; // no frame yet - the button stays
    el("camera-still").src = camera().stillDataUrl();
    cameraView("still");
  }

  function usePhoto() {
    var taken = camera().use();
    el("camera-still").removeAttribute("src");
    if (!taken) return; // nothing to use (a second tap); the screen stays as it is
    state.photoDataUrl = taken.dataUrl;
    state.photoTakenAt = taken.takenAt;
    state.cameraAvailable = true;
    sendPunch(state.pendingLogType);
  }

  function retakePhoto() {
    el("camera-still").removeAttribute("src");
    openCameraScreen();
  }

  function cancelCamera() {
    if (state.camera) state.camera.cancel();
    el("camera-still").removeAttribute("src");
    resetPunchState();
    show("home"); // nothing was sent; home is as it was
  }

  function punchWithoutPhoto() {
    if (state.camera) state.camera.cancel();
    state.cameraAvailable = false; // AC-200: the punch still counts, without a photo
    state.skipPhoto = true;
    sendPunch(state.pendingLogType);
  }

  function currentScreen() {
    var shown = app.querySelector(".screen:not([hidden])");
    return shown ? shown.getAttribute("data-screen") : null;
  }

  // The app went to the background (or the phone locked) with the preview
  // open: stop the camera now, and open it again when the app comes back.
  document.addEventListener("visibilitychange", function () {
    if (!state.camera) return;
    if (document.hidden) {
      state.cameraReopen = state.camera.pause();
    } else if (state.cameraReopen && currentScreen() === "camera") {
      state.cameraReopen = false;
      openCameraScreen();
    }
  });
  window.addEventListener("pagehide", function () {
    if (state.camera) state.camera.cancel();
  });

  function getPosition() {
    return new Promise(function (resolve, reject) {
      if (!navigator.geolocation) { reject({ code: "LOCATION_OFF" }); return; }
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        reject({ code: "LOCATION_SLOW" });
      }, 20000);
      navigator.geolocation.getCurrentPosition(function (pos) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(pos.coords);
      }, function (err) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        reject({ code: err && err.code === 1 ? "LOCATION_DENIED" : "LOCATION_OFF" });
      }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
    });
  }

  function doPunch(logType) {
    state.lastAction = "punch";
    state.pendingLogType = logType;
    if (state.photoDataUrl || state.skipPhoto) {
      sendPunch(logType); // AC-205: Try again resends the SAME photo, no new camera
      return;
    }
    openCameraScreen();
  }

  // The progress steps (01d §7.6): the photo, where you are, saving.
  function punchStep(which) {
    var order = ["photo", "where", "save"];
    var now = order.indexOf(which);
    order.forEach(function (name, i) {
      var step = el("punch-step-" + name);
      step.className = "step " + (i < now ? "done" : i === now ? "now" : "todo");
    });
    el("punching-status").textContent = which === "where" ? t("stepWhere") : t("stepSave");
  }

  function clearSlowTimer() {
    if (state.slowTimer) clearTimeout(state.slowTimer);
    state.slowTimer = null;
  }

  function sendPunch(logType) {
    state.lastAction = "punch";
    el("punching-title").textContent = logType === "OUT" ? t("checkingOut") : t("checkingIn");
    el("punch-step-photo-words").textContent = state.photoDataUrl ? t("stepPhoto") : t("stepNoPhoto");
    el("punching-slow").hidden = true;
    punchStep("where");
    show("punching");
    var photoDataUrl = state.photoDataUrl;
    clearSlowTimer();
    state.slowTimer = setTimeout(function () {
      el("punching-slow").textContent = photoDataUrl ? t("stillWorking") : t("stillWorkingNoPhoto");
      el("punching-slow").hidden = false;
    }, 10000);

    getPosition().then(function (coords) {
      return { photoDataUrl: photoDataUrl, coords: coords };
    }, function (locErr) {
      return { photoDataUrl: photoDataUrl, locErr: locErr };
    }).then(function (found) {
      if (found.locErr) {
        showProblem(found.locErr.code, {});
        return;
      }
      punchStep("save");
      window.AlvoraaApi.punch(state.origin, {
        token: state.secret,
        log_type: logType,
        latitude: found.coords.latitude,
        longitude: found.coords.longitude,
        accuracy: found.coords.accuracy,
        photo: found.photoDataUrl || undefined,
        // The phone's local time WITH its offset from UTC, so the server can
        // put it in the site's time zone (before 0.2.1: UTC with no mark,
        // stored 5 h 30 min early). The photo's own moment when there is one.
        captured_at: window.AlvoraaCheckinScreens.localTimeWithOffset(state.photoTakenAt || new Date()),
        // SEC-21 wants Android's own "is this a fake GPS provider" flag. The
        // Web API this file uses has no such field, so this is always 0 here -
        // a declared gap against SEC-21/AC-204, not something it pretends to do.
        mock_location: 0,
      }).then(function (result) {
        clearSlowTimer();
        if (result.ok) {
          var photo = found.photoDataUrl;
          resetPunchState();
          showResult(result.data, logType, photo, found.coords.accuracy);
        } else if (result.code === "NOTICE_CHANGED") {
          state.noticeAgainValues = result.values;
          renderNoticeAgain(result.values);
        } else if (isSignedOut(result.code)) {
          resetPunchState();
          signInAgain();
        } else {
          showProblem(result.code, result.values);
        }
      });
    });
  }

  function showResult(data, logType, photo, phoneAccuracy) {
    el("result-heading").textContent = logType === "IN" ? t("statusIn") : t("statusOut");
    el("result-time").textContent = clockOnly(data.time);
    var when = new Date(String(data.time).replace(" ", "T"));
    el("result-date").textContent = isNaN(when.getTime()) ? "" : ui.dayDate(when);
    // 27 Sep 2026: from the server's measurement, never the workplace's name
    // alone - "At <workplace>" only when the person was inside its radius.
    var where = screens.whereLines(data.location, phoneAccuracy);
    var items = [{ lead: where.icon, hl: where.headline, sup: where.detail }];
    if (photo) {
      var thumb = document.createElement("img");
      thumb.className = "thumb";
      thumb.alt = t("yourPhoto");
      thumb.src = photo;
      items.push({ lead: thumb, hl: t("resultPhotoTaken") });
    } else {
      items.push({ lead: "camera", hl: t("resultPhotoNotTaken"), sup: t("resultNoPhotoNote") });
    }
    items.push({ lead: "shield", hl: t("resultInRecord") });
    ui.fillList(el("result-card"), items);
    show("result");
  }

  // ── the notice again: changed, never agreed, or withdrawn (US-42) ───────

  function tickError(on) {
    el("notice-again-tick-error").hidden = !on;
    el("notice-again-row").classList.toggle("err", on);
  }

  function renderNoticeAgain(values, mode) {
    values = values || {};
    // Which moment is this? The notice cache is written only once the person
    // has agreed, and marked after "Stop agreeing" (ALV-133, M3-10):
    //   withdrawn  "You stopped agreeing" - never "before your first check-in";
    //   first      never agreed on this phone (closed on the first notice);
    //   changed    agreed before, and the words have moved on.
    var cached = window.AlvoraaNoticeCache.load();
    var kind = mode || (!cached ? "first" : cached.withdrawn ? "withdrawn" : "changed");
    var heading = { first: "Before you start", changed: "The notice has changed",
                    withdrawn: t("withdrawnHeading") }[kind];
    var intro = { first: "Please read this and agree before your first check-in.",
                  changed: "Please read it again before your next check-in.",
                  withdrawn: t("withdrawnIntro") }[kind];
    el("notice-again-heading").textContent = heading;
    el("notice-again-intro").textContent = intro;
    el("notice-again-changed-card").hidden = kind !== "changed" || !values.what_changed;
    el("notice-again-changed").textContent = values.what_changed || "";
    ui.renderNoticeRows(el("notice-again-rows"), values.rows);
    el("notice-again-version").textContent = values.version ? t("noticeVersion", { version: values.version }) : "";
    el("notice-again-agree-words").textContent = "I have read this and I understand.";
    el("notice-again-tick").checked = false;
    tickError(false);
    show("noticeAgain");
  }

  function agreeToNoticeAgain() {
    if (!el("notice-again-tick").checked) {
      tickError(true);
      el("notice-again-tick").focus();
      return;
    }
    state.lastAction = "notice";
    var version = state.noticeAgainValues && state.noticeAgainValues.version;
    window.AlvoraaApi.acknowledgeNotice(state.origin, state.secret, version).then(function (result) {
      if (!result.ok) {
        if (isSignedOut(result.code)) {
          signInAgain();
          return;
        }
        showProblem(result.code, result.values);
        return;
      }
      window.AlvoraaNoticeCache.save({
        version: version,
        rows: (state.noticeAgainValues && state.noticeAgainValues.rows) || [],
        agree: "I have read this and I understand.",
        retentionDays: state.noticeAgainValues && state.noticeAgainValues.retention_days,
        agreedAt: new Date().toISOString().replace("T", " ").slice(0, 19),
      });
      loadStatus();
    });
  }

  // ── Stop agreeing to the notice (ALV-133, 01d §7.8) ─────────────────────
  //
  // As easy to withdraw as to agree: one row in Settings, one dialog. The
  // server keeps the phone and every record, moves it to "Consent not given"
  // and writes it on the phone's timeline for HR (E-5). The notice then
  // opens with its own words; agreeing again is the way back, no new code.

  function openWithdraw() {
    el("withdraw-error").hidden = true;
    ui.openOverlay("dialog-withdraw");
  }

  function doWithdraw() {
    state.lastAction = "withdraw";
    window.AlvoraaApi.withdrawAgreement(state.origin, state.secret).then(function (result) {
      if (result.ok) {
        ui.closeOverlay("dialog-withdraw");
        window.AlvoraaNoticeCache.markWithdrawn();
        probeNotice("withdrawn");
        ui.snackbar(t("withdrawnSnackbar"));
        return;
      }
      if (result.code === "NO_INTERNET") {
        // Nothing changed on the server; say so inside the dialog.
        el("withdraw-error").textContent = "Connect to the internet to stop agreeing. Nothing has changed.";
        el("withdraw-error").hidden = false;
        return;
      }
      if (isSignedOut(result.code)) {
        signInAgain();
        return;
      }
      handleGateRefusal(result.code, result.values);
    });
  }

  // ── Settings (US-43, 01d §7.8) ──────────────────────────────────────────

  function renderSettings() {
    var data = state.status || {};
    var name = data.employee_name || data.first_name || "";
    el("settings-avatar").textContent = ui.initials(name);
    el("settings-name").textContent = name;
    el("settings-you").textContent = [data.designation, state.company].filter(Boolean).join(" · ");

    var rule = screens.homeRule(data);
    ui.fillList(el("settings-workplace"), [{
      lead: "pin",
      hl: state.workplaceName || t("noWorkplace"),
      sup: rule.kind === "radius"
        ? t("rulePlainWithin", { radius: Math.round(Number(state.radiusM)) })
        : t("rulePlainAnywhere"),
    }]);

    // D15/AC-224: the language row exists in the DOM only in a debug build -
    // not merely hidden, so it cannot be reached in pilot or release. No
    // screen has Hindi text yet (Hindi is not in ALV-133's scope).
    var languageBox = el("settings-language");
    clearChildren(languageBox);
    var buildType = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
    if (buildType === "debug") {
      languageBox.appendChild(textEl("h2", "Language", "section-h"));
      languageBox.appendChild(textEl("p",
        "Debug only. No screen has Hindi text yet, so this does not change anything visible.",
        "t-body-m muted u-help-line"));
      [["English", true], ["हिंदी", false]].forEach(function (pair) {
        var row = document.createElement("label");
        row.className = "radio-row";
        var input = document.createElement("input");
        input.type = "radio"; input.name = "alvoraa-language"; input.checked = pair[1]; input.disabled = true;
        row.appendChild(input);
        row.appendChild(document.createTextNode(pair[0]));
        languageBox.appendChild(row);
      });
    }

    var cached = window.AlvoraaNoticeCache.load();
    el("settings-agreed-on").textContent = cached && cached.agreedAt && !cached.withdrawn
      ? t("agreedOn", { when: ui.formatWhen(cached.agreedAt) }) : "";
    el("settings-agreed-on").hidden = !el("settings-agreed-on").textContent;
    el("settings-company-a").textContent = state.company;

    ui.fillList(el("settings-about"), [{
      lead: "info",
      hl: t("appVersion", { version: window.AlvoraaVersion ? window.AlvoraaVersion.APP_VERSION : "" }),
      sup: t("connectedTo", { host: (state.origin || "").replace(/^https:\/\//, "") }),
    }]);

    show("settings");
  }

  function renderRecords() {
    var cached = window.AlvoraaNoticeCache.load();
    var rowsBox = el("records-rows");
    if (cached && cached.rows && cached.rows.length) {
      ui.renderNoticeRows(rowsBox, cached.rows);
      el("records-agreed").textContent = t("agreedCard", {
        when: ui.formatWhen(cached.agreedAt) || "unknown", version: cached.version || "unknown" });
      el("records-agreed-card").hidden = false;
    } else {
      // The one honest fallback when the cache is empty (a WebView that
      // clears localStorage, or a phone joined before this cache existed).
      clearChildren(rowsBox);
      rowsBox.appendChild(textEl("p",
        "The full notice text is not saved on this phone. Ask HR to show you what was agreed.",
        "t-body-l notice-row"));
      el("records-agreed-card").hidden = true;
    }
    var rows = (state.status && state.status.todays_checkins) || [];
    var today = el("records-today");
    if (rows.length) {
      ui.fillList(today, rows.map(function (row) {
        var isIn = row.log_type === "IN";
        return { lead: isIn ? "login" : "logout",
                 hl: (isIn ? t("punchIn") : t("punchOut")) + " · " + clockOnly(row.time),
                 sup: t("recordedTodayLine") };
      }));
    } else {
      ui.fillList(today, [{ lead: "clock", hl: t("nothingToday") }]);
    }
    show("records");
  }

  // ── Remove this phone: one bottom sheet, one confirmation (01d §7.8) ────

  function openRemoveSheet(local) {
    // local: a final, dead-end phone state (blocked/replaced/left, AC-210).
    // The server has already refused this phone, so removing is local only:
    // no internet needed, and there is nothing new for HR to see.
    state.removeLocal = !!local;
    el("leave-company").textContent = state.company || "";
    el("leave-error").hidden = true;
    el("sheet-remove-hr").hidden = !!local;
    el("sheet-remove-internet").hidden = !!local;
    ui.openOverlay("sheet-remove");
  }

  function confirmRemove() {
    if (state.removeLocal) {
      forgetPhoneLocally().then(function () { window.AlvoraaJoin.start(); });
      return;
    }
    doRemove();
  }

  function doRemove() {
    state.lastAction = "remove";
    window.AlvoraaApi.removeMyPhone(state.origin, state.secret).then(function (result) {
      if (result.ok) {
        forgetPhoneLocally().then(function () { window.AlvoraaJoin.start(); });
        return;
      }
      if (result.code === "NO_INTERNET") {
        el("leave-error").hidden = false;
        el("leave-error").textContent = "Connect to the internet to remove this phone. Nothing has changed.";
        return;
      }
      // Already gone from the server's point of view (DEVICE_REMOVED etc.) -
      // the local effect is the same either way: forget it here too.
      forgetPhoneLocally().then(function () { window.AlvoraaJoin.start(); });
    });
  }

  // ── wiring ────────────────────────────────────────────────────────────────

  el("notice-again-tick").addEventListener("change", function () {
    if (el("notice-again-tick").checked) tickError(false);
  });

  var ACTIONS = {
    "checkin-punch": pressPunch,
    "checkin-loc-continue": continueFromLocExplain,
    "checkin-camera-take": takePhoto,
    "checkin-camera-use": usePhoto,
    "checkin-camera-retake": retakePhoto,
    "checkin-camera-cancel": cancelCamera,
    "checkin-camera-try-again": openCameraScreen,
    "checkin-camera-no-photo": punchWithoutPhoto,
    "checkin-camera-retry": function () { state.cameraAvailable = undefined; loadStatus(); },
    "checkin-result-done": loadStatus,
    "checkin-open-settings": renderSettings,
    "checkin-settings-back": loadStatus,
    "checkin-open-records": renderRecords,
    "checkin-records-back": renderSettings,
    "checkin-open-withdraw": openWithdraw,
    "checkin-withdraw-keep": function () { ui.closeOverlay("dialog-withdraw"); },
    "checkin-withdraw-confirm": doWithdraw,
    "checkin-open-leave-confirm": function () { openRemoveSheet(false); },
    "checkin-open-leave-confirm-from-gate": function () { openRemoveSheet(false); },
    "checkin-remove-confirm": confirmRemove,
    "checkin-remove-keep": function () { ui.closeOverlay("sheet-remove"); },
    "checkin-local-remove": function () { openRemoveSheet(true); },
    "checkin-notice-agree": agreeToNoticeAgain,
    "checkin-retry-status": loadStatus,
    "checkin-retry-last": retryLast,
    "checkin-go-home": loadStatus,
    "checkin-check-update": loadStatus,
    // "Open phone settings" for a location denial: the same best effort
    // join.js uses for the camera (no vetted plugin opens Android's per-app
    // settings page yet). Retrying re-shows the prompt on some WebViews.
    "checkin-open-os-settings": retryLast,
  };

  app.addEventListener("click", function (event) {
    var target = event.target.closest && event.target.closest("[data-action]");
    if (!target) return;
    var action = ACTIONS[target.getAttribute("data-action")];
    if (action) action();
  });

  window.AlvoraaCheckin = { start: start };
})();
