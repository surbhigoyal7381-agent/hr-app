/*
 * The daily-use flow, wired up for real: the Attendance screen and the punch
 * (US-39), the punch's own problem screens (US-40), the gate the app runs
 * through on every open (the "on open" half of US-41), the changed-notice
 * screen (US-42), and Settings (US-43). Slice 013, daily use.
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

  function el(id) { return document.getElementById(id); }

  function show(name) {
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
  //    before? (AC-198: only the FIRST check-in ever shows it.) Not worth a
  //    module of its own - one boolean, wrapped the same fail-soft way
  //    notice-cache.js wraps localStorage, so a WebView that blocks storage
  //    just asks again every time rather than crashing.
  var LOCATION_EXPLAINED_KEY = "alvoraa_location_explained";
  function hasSeenLocationExplain() {
    try { return localStorage.getItem(LOCATION_EXPLAINED_KEY) === "1"; } catch (e) { return false; }
  }
  function markLocationExplainSeen() {
    try { localStorage.setItem(LOCATION_EXPLAINED_KEY, "1"); } catch (e) { /* fail soft */ }
  }

  // ── state - nothing here is written to disk except through the two
  //    modules that are meant to (device-secret.js, notice-cache.js) ───────
  var state = {
    origin: null,
    secret: null,
    company: null,
    workplaceName: null,
    radiusM: null,
    checkedIn: false,
    minVersion: null,
    lastAction: null,        // "status" | "punch" | "remove" | "notice"
    pendingLogType: null,    // "IN" or "OUT" - what Try again resends
    photoDataUrl: null,      // kept across Try again (AC-205)
    stream: null,
    noticeAgainValues: null, // the six rows to re-render on noticeAgain
    removeReason: null,      // "settings" | "gate" - which screen asked for E6
  };

  function stopCamera() {
    if (state.stream) {
      state.stream.getTracks().forEach(function (t) { t.stop(); });
      state.stream = null;
    }
  }

  function resetPunchState() {
    state.photoDataUrl = null;
    state.pendingLogType = null;
  }

  // ── the shared problem screen (reuses index.html's #problem, exactly as
  //    join.js's own showProblem does - only one of the two ever runs at a
  //    time, so there is no collision in practice) ─────────────────────────

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
    update: [], // its one button is built dynamically below, by build type
  };

  // 05-review-daily-use.md, M1: the card is rendered through the SAME shared
  // helper join.js uses (problem-card.js), so there is one place, not two,
  // that decides what #problem-card shows - and every call clears it first,
  // so a card this file showed earlier can never survive into a screen the
  // OTHER file (join.js) shows next. `appVersion`/`when` are filled in here
  // (not inside the shared helper) because those come from this file's own
  // globals/clock, and the helper stays a pure function of its arguments.
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
  }

  function showProblem(code, values, opts) {
    stopCamera();
    // Remembered so "Keep it" on a Remove-confirm opened FROM one of these
    // gate screens (appOff/notField) returns to the exact right one, not a
    // guess (see openLeaveConfirm/ "checkin-remove-keep" below).
    state.lastGateCode = code;
    state.lastGateValues = values;
    var info = window.AlvoraaCheckinScreens.screenFor(code, values, Object.assign({ company: state.company }, opts || {}));
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
      // OPS-58 asks for a live "Update in Play Store"/tester link per build
      // type. This app's own bundle rules (SEC-16/OPS-22, enforced by
      // scripts/check_app.mjs's outside-URL check) refuse ANY hardcoded
      // address outside *.alvoraa.co, and no real Play listing or Firebase
      // tester link exists yet to embed even if that rule did not apply.
      // Rather than fabricate a URL that would either fail that guardrail or
      // silently point nowhere, this build gives plain instructions instead
      // of a button - a declared, deliberate gap against OPS-58, not a
      // silent one. Testers already receive their own download link by email
      // (AC-230), so pilot does not need one embedded here either.
      var buildType = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
      var guidance = buildType === "debug" ? "Ask the developer."
        : buildType === "pilot" ? "Ask HR for the update link you were sent."
        : "Open the Play Store and search for Alvoraa, or ask HR.";
      buttonsBox.appendChild(textEl("p", guidance, "small"));
    } else {
      var actions = PROBLEM_ACTIONS[info.screen] || [];
      (info.buttons || []).forEach(function (btnLabel, i) {
        var button = textEl("button", btnLabel);
        button.type = "button";
        button.setAttribute("data-action", actions[i] || "checkin-go-home");
        buttonsBox.appendChild(button);
      });
    }

    el("problem-footer").textContent = "Code for HR: " + info.footerCode;
    show("problem");
  }

  function retryLast() {
    if (state.lastAction === "status") loadStatus();
    else if (state.lastAction === "punch") doPunch(state.pendingLogType);
    else if (state.lastAction === "remove") doRemove();
    else if (state.lastAction === "notice") agreeToNoticeAgain();
    else show("home");
  }

  // ── boot: does this phone have a secret? then call field_status (E4) ────

  /*
   * opts.autoPunch: true when the join flow's own "Check In" button (01b's
   * `welcome` screen) sent us here - the flow is welcome -> Check In ->
   * locExplain -> punching directly, not via home first (01b §6's flow
   * diagram). "Not now" calls start() with no options, landing on home
   * unchecked-in, which is also exactly what a normal app open does.
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
        // at all from the person's point of view - never guess, go back to
        // the join flow's own first launch.
        window.AlvoraaJoin.start();
        return;
      }
      loadStatus();
    });
  }

  function forgetPhoneLocally() {
    stopCamera();
    return window.AlvoraaDeviceSecret.clear().then(function () {
      window.AlvoraaNoticeCache.clear();
    });
  }

  function loadStatus() {
    state.lastAction = "status";
    window.AlvoraaApi.fieldStatus(state.origin, state.secret).then(function (result) {
      if (result.ok) {
        renderHome(result.data);
        return;
      }
      handleGateRefusal(result.code, result.values);
    });
  }

  function handleGateRefusal(code, values) {
    var plan = window.AlvoraaGateRefusal.planForGateRefusal(code, values);
    if (plan.action === "forgetAndFirst") {
      forgetPhoneLocally().then(function () {
        window.AlvoraaJoin.start();
        // DEVICE_REMOVED's own line ("This phone is no longer linked to
        // {company}.") needs a place on the first-launch screen to sit; that
        // markup is join.js's, so the exact line is left for whoever adds it
        // there (see 03-implementation-notes.md's declared gaps).
      });
      return;
    }
    if (plan.action === "noticeAgain") {
      state.noticeAgainValues = plan.values;
      renderNoticeAgain(plan.values);
      return;
    }
    if (plan.action === "probeConsentRequired") {
      // 05-review-daily-use.md, M2: CONSENT_REQUIRED's own values carry only
      // `version`, not the six rows (field_app_errors.CODES), so the full
      // text is fetched the same way a stale notice_version already is: send
      // acknowledge_notice a version it cannot possibly match, which makes
      // the server refuse with NOTICE_CHANGED and the full rows attached -
      // no new server endpoint, no client-side guess at the words. See
      // gate-refusal.js for exactly why this state needs recovering at all.
      state.lastAction = "status";
      window.AlvoraaApi.acknowledgeNotice(state.origin, state.secret, "").then(function (result) {
        var probePlan = window.AlvoraaGateRefusal.planForConsentRequiredProbe(result);
        if (probePlan.action === "noticeAgain") {
          state.noticeAgainValues = probePlan.values;
          renderNoticeAgain(probePlan.values);
        } else if (probePlan.action === "reloadStatus") {
          loadStatus();
        } else {
          showProblem(probePlan.code, probePlan.values);
        }
      });
      return;
    }
    showProblem(plan.code, plan.values);
  }

  // ── the Attendance screen (US-39, AC-197) ────────────────────────────────

  function renderHome(data) {
    state.company = data.company || "";
    state.checkedIn = !!data.checked_in;
    state.workplaceName = data.workplace && data.workplace.name;
    state.radiusM = data.workplace && data.workplace.radius_m;
    state.minVersion = data.min_version;

    el("home-company").textContent = state.company;
    el("home-person").textContent = data.employee_name || data.first_name || "";

    var rows = data.todays_checkins || [];
    var last = rows.length ? rows[rows.length - 1] : null;
    var statusLine = el("home-status");
    var statusText = el("home-status-text");
    statusLine.classList.remove("in");
    if (!last) {
      statusText.textContent = "Not checked in yet today";
    } else if (last.log_type === "IN") {
      statusText.textContent = "Checked in since " + clockOnly(last.time);
      statusLine.classList.add("in");
    } else {
      // FC-1, built correctly the first time: an "out" state never claims
      // "not checked in yet today" - it says what actually happened.
      statusText.textContent = "Checked out at " + clockOnly(last.time);
    }

    var ruleLine = el("home-rule");
    if (state.workplaceName && state.radiusM) {
      ruleLine.textContent = "You need to be within " + state.radiusM + " m of " + state.workplaceName;
      ruleLine.hidden = false;
    } else {
      ruleLine.hidden = true;
    }

    var button = el("home-punch-button");
    button.textContent = state.checkedIn ? "Check Out" : "Check In";
    button.className = state.checkedIn ? "primary-purple" : "primary-green";

    var list = el("home-punch-list");
    clearChildren(list);
    if (!rows.length) {
      list.appendChild(textEl("p", "No punches yet today.", "small"));
    } else {
      rows.forEach(function (row) {
        var line = document.createElement("div");
        line.className = "punch-row";
        line.appendChild(textEl("span", row.log_type === "IN" ? "Checked in" : "Checked out"));
        line.appendChild(textEl("span", clockOnly(row.time)));
        list.appendChild(line);
      });
    }

    el("home-camera-off").hidden = state.cameraAvailable !== false;

    if (state.autoPunch) {
      // 01b §6: welcome's own "Check In" goes straight into the punch, not
      // through a first tap on home. Only ever fires once per start() call,
      // and only when there is really something to check in to (a blocked/
      // replaced/etc. phone never reaches renderHome at all).
      state.autoPunch = false;
      pressPunch();
      return;
    }
    show("home");
  }

  function clockOnly(value) {
    var d = new Date(String(value).replace(" ", "T"));
    if (isNaN(d.getTime())) return String(value || "");
    var h = d.getHours();
    var ampm = h < 12 ? "am" : "pm";
    var h12 = h % 12 || 12;
    var m = d.getMinutes();
    return h12 + ":" + (m < 10 ? "0" + m : m) + " " + ampm;
  }

  // ── Check In / Check Out ─────────────────────────────────────────────────

  function pressPunch() {
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

  function capturePunchPhoto() {
    // Reuses the exact getUserMedia + canvas + photo.js pipeline join.js's
    // scanner already proves works in this WebView (09-install-the-test-app.md),
    // aimed at the still-image case instead of a continuous decode loop.
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.resolve(null);
    }
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } },
      audio: false,
    }).then(function (stream) {
      return new Promise(function (resolve) {
        var video = document.createElement("video");
        video.playsInline = true;
        video.muted = true;
        video.srcObject = stream;
        video.play();
        video.addEventListener("loadeddata", function once() {
          video.removeEventListener("loadeddata", once);
          var shrunk = window.AlvoraaPhoto.shrinkToJpeg(video, video.videoWidth, video.videoHeight);
          stream.getTracks().forEach(function (t) { t.stop(); });
          resolve(shrunk ? shrunk.dataUrl : null);
        }, { once: true });
      });
    }).catch(function () {
      return null; // denied, or no camera - punch still counts (AC-200)
    });
  }

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
    show("punching");
    el("punching-status").textContent = "Taking your photo";

    var photoPromise = state.photoDataUrl
      ? Promise.resolve(state.photoDataUrl) // AC-205: Try again resends the SAME photo
      : capturePunchPhoto().then(function (dataUrl) {
          state.cameraAvailable = !!dataUrl;
          state.photoDataUrl = dataUrl;
          return dataUrl;
        });

    photoPromise.then(function (photoDataUrl) {
      el("punching-status").textContent = "Finding where you are";
      return getPosition().then(function (coords) {
        return { photoDataUrl: photoDataUrl, coords: coords };
      }, function (locErr) {
        return { photoDataUrl: photoDataUrl, locErr: locErr };
      });
    }).then(function (found) {
      if (found.locErr) {
        showProblem(found.locErr.code, {});
        return;
      }
      el("punching-status").textContent = "Saving your attendance";
      window.AlvoraaApi.punch(state.origin, {
        token: state.secret,
        log_type: logType,
        latitude: found.coords.latitude,
        longitude: found.coords.longitude,
        accuracy: found.coords.accuracy,
        photo: found.photoDataUrl || undefined,
        captured_at: new Date().toISOString().replace("T", " ").slice(0, 19),
        // SEC-21 wants Android's own "is this a fake GPS provider" flag.
        // The standard `navigator.geolocation` Web API this file uses has no
        // such field - GeolocationCoordinates never carries one - so this is
        // always 0 here. Reading the real flag needs a native call (a
        // Capacitor Geolocation plugin, or a small bridge of our own), which
        // this build deliberately does not add (00-impact-analysis-daily-use.md
        // chose plain Web APIs to keep the dependency and permission surface
        // at what US-39 already needs). Declared as a known gap against
        // SEC-21/AC-204, not something this code pretends to do.
        mock_location: 0,
      }).then(function (result) {
        if (result.ok) {
          var hadPhoto = !!found.photoDataUrl;
          resetPunchState();
          showResult(result.data, logType, hadPhoto);
        } else if (result.code === "NOTICE_CHANGED") {
          state.noticeAgainValues = result.values;
          renderNoticeAgain(result.values);
        } else {
          showProblem(result.code, result.values);
        }
      });
    });
  }

  function showResult(data, logType, hadPhoto) {
    el("result-heading").textContent = logType === "IN" ? "Checked in" : "Checked out";
    el("result-time").textContent = clockOnly(data.time);
    var card = el("result-card");
    clearChildren(card);
    if (state.workplaceName) card.appendChild(textEl("p", "Where you were · At " + state.workplaceName));
    card.appendChild(textEl("p", hadPhoto ? "Photo · Taken" : "Photo · Not taken"));
    if (!hadPhoto) {
      card.appendChild(textEl("p", "The camera was not on. Your attendance still counts."));
    }
    card.appendChild(textEl("p", "Saved · In your HR record"));
    show("result");
  }

  // ── the changed notice, mid-daily-use (US-42) ────────────────────────────

  function renderNoticeAgain(values) {
    // ALV-128: a phone that has never agreed on this phone (closed on the first
    // notice after signing in) is reading it for the FIRST time - it must not
    // be told the notice "has changed". The notice cache is written only once
    // the person has agreed, so an empty cache is the sign.
    var firstTime = !window.AlvoraaNoticeCache.load();
    el("notice-again-heading").textContent = firstTime
      ? "Before you start" : "The notice has changed";
    el("notice-again-intro").textContent = firstTime
      ? "Please read this and agree before your first check-in."
      : "Please read it again before your next check-in.";
    el("notice-again-changed").hidden = firstTime;
    el("notice-again-changed").textContent = "What is new: " + (values.what_changed || "") + ".";
    var rowsBox = el("notice-again-rows");
    clearChildren(rowsBox);
    (values.rows || []).forEach(function (row) {
      rowsBox.appendChild(textEl("h3", row.heading));
      rowsBox.appendChild(textEl("p", row.body));
    });
    el("notice-again-agree-words").textContent = "I have read this and I understand.";
    el("notice-again-tick").checked = false;
    el("notice-again-tick-error").hidden = true;
    show("noticeAgain");
  }

  function agreeToNoticeAgain() {
    if (!el("notice-again-tick").checked) {
      el("notice-again-tick-error").hidden = false;
      el("notice-again-tick").focus();
      return;
    }
    state.lastAction = "notice";
    var version = state.noticeAgainValues && state.noticeAgainValues.version;
    window.AlvoraaApi.acknowledgeNotice(state.origin, state.secret, version).then(function (result) {
      if (!result.ok) {
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

  // ── Settings (US-43) ──────────────────────────────────────────────────────

  function renderSettings() {
    el("settings-you").textContent = (el("home-person").textContent || "")
      + (state.workplaceName ? " · " + state.company + " · " + state.workplaceName : " · " + state.company)
      + (state.radiusM ? " · Check in within " + state.radiusM + " m" : "");

    // D15/AC-224: the language row exists in the DOM only in a debug build -
    // not merely hidden, so it cannot be reached in pilot or release by any
    // input method. No screen in this app (or the already-shipped join
    // screens) has Hindi text yet, so this is a build-type-gated scaffold,
    // not a working translation - declared honestly in the implementation
    // notes, not left to be discovered later.
    var languageBox = el("settings-language");
    clearChildren(languageBox);
    var buildType = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
    if (buildType === "debug") {
      languageBox.appendChild(textEl("h3", "Language"));
      languageBox.appendChild(textEl("p",
        "Debug only. No screen has Hindi text yet, so this does not change anything visible.", "small"));
      var en = document.createElement("label");
      en.className = "radio-row";
      var enInput = document.createElement("input");
      enInput.type = "radio"; enInput.name = "alvoraa-language"; enInput.checked = true; enInput.disabled = true;
      en.appendChild(enInput);
      en.appendChild(document.createTextNode("English"));
      var hi = document.createElement("label");
      hi.className = "radio-row";
      var hiInput = document.createElement("input");
      hiInput.type = "radio"; hiInput.name = "alvoraa-language"; hiInput.disabled = true;
      hi.appendChild(hiInput);
      hi.appendChild(document.createTextNode("हिंदी"));
      languageBox.appendChild(en);
      languageBox.appendChild(hi);
    }

    var cached = window.AlvoraaNoticeCache.load();
    el("settings-agreed-on").textContent = cached && cached.agreedAt
      ? "You agreed on " + cached.agreedAt : "";
    el("settings-company-a").textContent = state.company;

    el("settings-about").textContent = "App version · " + (window.AlvoraaVersion ? window.AlvoraaVersion.APP_VERSION : "")
      + " · Connected to · " + (state.origin || "").replace(/^https:\/\//, "");

    show("settings");
  }

  function renderRecords() {
    var cached = window.AlvoraaNoticeCache.load();
    var rowsBox = el("records-rows");
    clearChildren(rowsBox);
    if (cached && cached.rows && cached.rows.length) {
      cached.rows.forEach(function (row) {
        rowsBox.appendChild(textEl("h3", row.heading));
        rowsBox.appendChild(textEl("p", row.body));
      });
      el("records-agreed").textContent = "You agreed on " + (cached.agreedAt || "unknown")
        + ". Notice version " + (cached.version || "unknown") + ".";
    } else {
      // The one honest fallback when the cache is empty (a WebView that
      // clears localStorage, or a phone joined before this cache existed):
      // still name the version from the last field_status answer rather than
      // showing nothing.
      rowsBox.appendChild(textEl("p",
        "The full notice text is not saved on this phone. Ask HR to show you what was agreed."));
    }
    show("records");
  }

  function openLeaveConfirm(reason) {
    state.removeReason = reason || "settings";
    el("leave-company").textContent = state.company || "";
    el("leave-error").hidden = true;
    show("leaveConfirm");
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

  function localRemoveFromGate() {
    // AC-210: for a final, dead-end phone state (blocked/replaced/left) the
    // server has already refused the phone - calling E6 here would only be
    // refused again. Remove is local-only, after a confirm (kept as the
    // platform's own confirm dialog rather than a new screen, a declared
    // shortcut - see the implementation notes).
    if (!window.confirm("Remove this phone from " + (state.company || "your company") + "? "
      + "You will need a new code from HR to use the app again.")) {
      return;
    }
    forgetPhoneLocally().then(function () { window.AlvoraaJoin.start(); });
  }

  // ── wiring ────────────────────────────────────────────────────────────────

  var ACTIONS = {
    "checkin-punch": pressPunch,
    "checkin-loc-continue": continueFromLocExplain,
    "checkin-camera-retry": function () { state.cameraAvailable = undefined; loadStatus(); },
    "checkin-result-done": loadStatus,
    "checkin-open-settings": renderSettings,
    "checkin-settings-back": loadStatus,
    "checkin-open-records": renderRecords,
    "checkin-records-back": renderSettings,
    "checkin-open-leave-confirm": function () { openLeaveConfirm("settings"); },
    "checkin-open-leave-confirm-from-gate": function () { openLeaveConfirm("gate"); },
    "checkin-remove-confirm": doRemove,
    "checkin-remove-keep": function () {
      if (state.removeReason === "gate") { showProblem(state.lastGateCode, state.lastGateValues); }
      else { renderSettings(); }
    },
    "checkin-local-remove": localRemoveFromGate,
    "checkin-notice-agree": agreeToNoticeAgain,
    "checkin-retry-status": loadStatus,
    "checkin-retry-last": retryLast,
    "checkin-go-home": loadStatus,
    "checkin-check-update": loadStatus,
    // "Open phone settings" for a location denial: same best-effort join.js
    // already uses for the camera (no vetted plugin opens Android's own
    // per-app settings page in this increment - see
    // 03-implementation-notes.md §8). Retrying the same call re-shows the OS
    // prompt on some WebViews unless "don't ask again" was chosen; if not,
    // "Go back" still works.
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
