/*
 * The sign-in screens (ALV-128): company code, work email and password; the
 * one-time code when two-factor sign-in is on; then the notice, then the
 * existing Welcome and Attendance screens.
 *
 * DOM only. Every decision - is the form filled in, is the company code a real
 * Alvoraa address, what does a server code mean - is in signin-core.js and
 * host-check.js, which have tests. Like join.js, every value from the server
 * is written with textContent, never as HTML.
 *
 * The password: read from its box when Sign in is pressed, put in that one
 * request body, and the box is emptied as soon as the answer comes back. It
 * is never written to storage, never kept in `state`, never logged. The
 * two-factor step does not send it again - the server's one-time id stands in
 * for it.
 *
 * After a good sign-in the phone holds its device secret, exactly as after a
 * QR join, and every later call (the punch, the start screen) is the same
 * token-based call a code-joined phone makes. The My HR tab can later be
 * unlocked by the same secret; nothing here needs to change for that.
 */
(function () {
  "use strict";

  var BUILD_TYPE = (window.AlvoraaBuildType && window.AlvoraaBuildType.BUILD_TYPE) || "release";
  var core = window.AlvoraaSigninCore;
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

  function textEl(tag, text) {
    var node = document.createElement(tag);
    node.textContent = text;
    return node;
  }

  // Memory only, for the length of one sign-in. Never the password.
  var state = {
    origin: null,
    email: null,
    tmpId: null,
    token: null,
    answer: null,   // the sign-in answer: first name, company, workplace, notice
    busy: false,
    // The secret this phone held before it was signed out for a password
    // change (memory only, never stored). Sent with the sign-in so the server
    // knows it is the same phone and sends no "new phone" email.
    previousToken: null,
  };

  function reset() {
    state.origin = null;
    state.email = null;
    state.tmpId = null;
    state.token = null;
    state.answer = null;
    state.busy = false;
    state.previousToken = null;
    el("signin-password").value = "";
    el("signin-otp").value = "";
    hideError("signin");
    hideError("signin-otp");
  }

  // ── errors under the form, in words, with the code for HR ────────────────

  function hideError(prefix) {
    el(prefix + "-error").hidden = true;
    el(prefix + "-error-code").hidden = true;
  }

  function showError(code, values, focusField) {
    var msg = core.messageFor(code, values);
    var prefix = msg.step === "otp" ? "signin-otp" : "signin";
    show(msg.step === "otp" ? "signinOtp" : "signin");
    el(prefix + "-error").textContent = msg.text;
    el(prefix + "-error").hidden = false;
    el(prefix + "-error-code").textContent = "Code for HR: " + msg.footerCode;
    el(prefix + "-error-code").hidden = false;
    var field = focusField ? el("signin-" + focusField) : null;
    if (field) field.focus();
  }

  // ── step 1: company code, email, password ────────────────────────────────

  function submitSignIn(event) {
    event.preventDefault();
    if (state.busy) return;
    hideError("signin");
    var passwordBox = el("signin-password");
    var checked = core.checkForm(el("signin-company").value, el("signin-email").value,
      passwordBox.value, BUILD_TYPE, window.AlvoraaHostCheck);
    if (!checked.ok) {
      showError(checked.code, {}, checked.field);
      return;
    }

    state.origin = checked.origin;
    state.email = checked.email;
    state.busy = true;
    show("signingIn");
    var request = window.AlvoraaApi.signInWithPassword(state.origin, {
      email: checked.email,
      password: passwordBox.value,
      device_label: "", // AC-220: model name only, once the app reads Device.getInfo()
      platform: "android",
      token: state.previousToken || undefined,
    });
    // Emptied now: the request already holds its own copy, and nothing else may.
    passwordBox.value = "";
    request.then(function (result) {
      state.busy = false;
      if (!result.ok) {
        showError(result.code, result.values, result.code === "COMPANY_CODE_INVALID" ? "company" : "password");
        return;
      }
      // The company code was right - remember it, so next time it is filled in.
      core.rememberCompany(checked.companyCode);
      if (result.data && result.data.status === "otp_required") {
        startOtp(result.data);
        return;
      }
      signedIn(result.data);
    });
  }

  // ── step 2 (only with two-factor sign-in): the one-time code ─────────────

  function startOtp(data) {
    state.tmpId = data.tmp_id;
    el("signin-otp").value = "";
    hideError("signin-otp");
    el("signin-otp-prompt").textContent = data.prompt
      || "Open your authenticator app, or check your email, for the code.";
    show("signinOtp");
    el("signin-otp").focus();
  }

  function submitOtp(event) {
    event.preventDefault();
    if (state.busy) return;
    hideError("signin-otp");
    var checked = core.checkOtp(el("signin-otp").value);
    if (!checked.ok) {
      showError(checked.code, {}, "otp");
      return;
    }
    state.busy = true;
    show("signingIn");
    window.AlvoraaApi.confirmSignInCode(state.origin, {
      tmp_id: state.tmpId,
      otp: checked.otp,
      device_label: "",
      platform: "android",
      token: state.previousToken || undefined,
    }).then(function (result) {
      state.busy = false;
      el("signin-otp").value = "";
      if (!result.ok) {
        if (result.code === "OTP_EXPIRED") state.tmpId = null;
        showError(result.code, result.values, result.code === "OTP_WRONG" ? "otp" : "password");
        return;
      }
      signedIn(result.data);
    });
  }

  // ── signed in: keep the secret, then the notice ──────────────────────────

  function signedIn(data) {
    state.answer = data;
    state.token = data.token;
    // The server has set the phone up; keep its secret and its company now,
    // in the same order join.js does (secret first, then the origin). If the
    // app is closed before the notice is agreed, the next open finds the
    // secret, and the Attendance screen asks for the notice itself.
    window.AlvoraaDeviceSecret.save(data.token)
      .then(function () { return window.AlvoraaDeviceSecret.saveOrigin(state.origin); })
      .then(function () {
        if (data.status === "active") {
          finish();
        } else {
          renderNotice();
        }
      })
      .catch(function () {
        showError("SERVER_ERROR", {});
      });
  }

  function renderNotice() {
    var data = state.answer || {};
    var notice = data.notice || {};
    el("signin-notice-topbar").textContent = [data.company, data.first_name].filter(Boolean).join(" · ");
    el("signin-notice-intro").textContent = (data.company || "Your company")
      + " asks you to read this. It says what the app records about you.";
    var rows = el("signin-notice-rows");
    clearChildren(rows);
    (notice.rows || []).forEach(function (row) {
      rows.appendChild(textEl("h3", row.heading));
      rows.appendChild(textEl("p", row.body));
    });
    el("signin-notice-agree-words").textContent = notice.agree || "I have read this and I understand.";
    el("signin-notice-tick").checked = false;
    el("signin-notice-error").hidden = true;
    show("signinNotice");
  }

  function agree() {
    if (state.busy) return;
    var error = el("signin-notice-error");
    if (!el("signin-notice-tick").checked) {
      error.textContent = "Please tick the box to show you have read the notice.";
      error.hidden = false;
      el("signin-notice-tick").focus();
      return;
    }
    error.hidden = true;
    var notice = (state.answer && state.answer.notice) || {};
    state.busy = true;
    window.AlvoraaApi.acknowledgeNotice(state.origin, state.token, notice.version).then(function (result) {
      state.busy = false;
      if (!result.ok) {
        if (result.code === "NOTICE_CHANGED" && result.values && result.values.rows) {
          state.answer.notice = Object.assign({}, notice, result.values);
          renderNotice();
          error.textContent = "The notice has just changed. Please read it again.";
          error.hidden = false;
          return;
        }
        error.textContent = core.messageFor(result.code, result.values).text
          + " (Code for HR: " + result.code + ")";
        error.hidden = false;
        return;
      }
      finish();
    });
  }

  function finish() {
    var data = state.answer || {};
    var notice = data.notice || {};
    window.AlvoraaNoticeCache.save({
      version: notice.version,
      rows: notice.rows || [],
      agree: notice.agree,
      retentionDays: notice.retention_days,
      // The phone's own clock, for display only (as in join.js).
      agreedAt: new Date().toISOString().replace("T", " ").slice(0, 19),
    });
    el("welcome-heading").textContent = "Welcome, " + (data.first_name || "") + ". This phone is set up.";
    var card = el("welcome-card");
    clearChildren(card);
    card.appendChild(textEl("p", "Company · " + (data.company || "")));
    if (data.workplace && data.workplace.name) {
      card.appendChild(textEl("p", "Your workplace · " + data.workplace.name));
      card.appendChild(textEl("p", "Check in within · " + data.workplace.radius_m + " m"));
    }
    // Nothing from this sign-in stays in memory past this point.
    state.answer = null;
    state.token = null;
    state.tmpId = null;
    state.previousToken = null;
    show("welcome");  // its buttons are join.js's: they hand over to the Attendance screen
  }

  // ── wiring ───────────────────────────────────────────────────────────────

  el("signin-form").addEventListener("submit", submitSignIn);
  el("signin-otp-form").addEventListener("submit", submitOtp);

  var ACTIONS = {
    "signin-use-code": function () { reset(); window.AlvoraaJoin.startQr(); },
    "signin-open": function () { start(); },
    "signin-start-again": function () { start(); },
    "signin-agree": agree,
  };

  app.addEventListener("click", function (event) {
    var target = event.target.closest && event.target.closest("[data-action]");
    if (!target) return;
    var action = ACTIONS[target.getAttribute("data-action")];
    if (action) action();
  });

  /*
   * opts (optional):
   *   reason         a server code to explain on the form, e.g.
   *                  PASSWORD_CHANGED_SIGN_IN_AGAIN ("Your password was
   *                  changed. Please sign in again.")
   *   previousToken  the secret the phone held (memory only)
   *   origin         the address the phone was using, for the company code
   *                  when none is remembered
   */
  function start(opts) {
    opts = opts || {};
    reset();
    state.previousToken = typeof opts.previousToken === "string" ? opts.previousToken : null;
    el("signin-company").value = core.rememberedCompany() || core.companyFromOrigin(opts.origin);
    show("signin");
    if (opts.reason) {
      showError(opts.reason, {}, el("signin-company").value ? "password" : "company");
    }
  }

  window.AlvoraaSignin = { start: start };
})();
