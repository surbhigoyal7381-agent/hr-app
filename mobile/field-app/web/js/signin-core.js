/*
 * Signing in with a work email and password (ALV-128): the decisions, with no
 * DOM. signin.js only puts on the screen what this returns, the same split
 * join-screens.js and join.js already use.
 *
 * Three jobs:
 *   checkForm()     is the form filled in well enough to send? Refused here
 *                   BEFORE any network call, so a typo never costs a try
 *                   against the account's lockout.
 *   messageFor()    one plain sentence for every answer the sign-in can get,
 *                   and which step to show it on ("form" or "otp"). The app
 *                   picks it from the server's `code` alone, never from the
 *                   English words Frappe also sends (MA-30).
 *   What is kept:   only the company code, so the person types it once. The
 *                   password is never kept - not here, not anywhere.
 *
 * Works as a plain browser script (window.AlvoraaSigninCore) and in Node tests.
 */
(function (root) {
  "use strict";

  var MAX_EMAIL = 140;      // a login's name on the server is at most 140
  var MAX_PASSWORD = 512;   // Frappe's own ceiling
  var MAX_OTP = 12;

  function waitMinutes(seconds) {
    var s = Number(seconds);
    if (!(s > 0)) return "a few minutes";
    var m = Math.ceil(s / 60);
    return m <= 1 ? "one minute" : m + " minutes";
  }

  /*
   * company   what was typed in the company box
   * email     what was typed in the email box
   * password  what was typed in the password box (read, never kept)
   * buildType "debug" | "pilot" | "release"
   * hostCheck the AlvoraaHostCheck module (injected so a test can pass it)
   *
   * Returns { ok: true, origin, companyCode, email } or
   *         { ok: false, code, field } - field is the input to put focus on.
   */
  function checkForm(company, email, password, buildType, hostCheck) {
    var where = hostCheck.originForCompanyCode(company || "", buildType);
    if (!where.ok) return { ok: false, code: "COMPANY_CODE_INVALID", field: "company" };
    var cleanEmail = typeof email === "string" ? email.trim() : "";
    if (!cleanEmail || cleanEmail.length > MAX_EMAIL || cleanEmail.indexOf("@") < 1) {
      return { ok: false, code: "EMAIL_INVALID", field: "email" };
    }
    if (typeof password !== "string" || password.length === 0 || password.length > MAX_PASSWORD) {
      return { ok: false, code: "PASSWORD_MISSING", field: "password" };
    }
    return { ok: true, origin: where.origin, companyCode: where.code, email: cleanEmail };
  }

  function checkOtp(otp) {
    var clean = typeof otp === "string" ? otp.replace(/\s+/g, "") : "";
    if (!clean || clean.length > MAX_OTP) return { ok: false, code: "OTP_MISSING", field: "otp" };
    return { ok: true, otp: clean };
  }

  // code -> [step, sentence]. step "form" shows it under the sign-in form;
  // "otp" under the one-time code box. OTP_EXPIRED goes back to the form,
  // because the only way on is to sign in again.
  var MESSAGES = {
    // made by this app, before any call
    COMPANY_CODE_INVALID: ["form", "Check your company code. It is the short name HR gave you, for example the first part of your company's Alvoraa web address."],
    EMAIL_INVALID: ["form", "Type your work email address."],
    PASSWORD_MISSING: ["form", "Type your password."],
    OTP_MISSING: ["otp", "Type the code you were sent."],
    NO_INTERNET: ["form", "No internet. Move to a place with signal and try again. Nothing was sent."],

    // the server's answers
    SIGN_IN_FAILED: ["form", "That email and password do not match. Check them and try again. If you forgot your password, reset it on your company's Alvoraa website."],
    ACCOUNT_LOCKED: ["form", null],   // needs the wait, see below
    // Frappe's lock on the network (many failures from one address), not on
    // this account - so it must not say "your account".
    // Security's words (27 Sep 2026, D-M3-6): Frappe's per-network lock after
    // repeated wrong passwords lasts minutes; mobile data is a different network.
    NETWORK_LOCKED: ["form", "Too many wrong sign-in attempts from this network. Try again in a few minutes, or turn off Wi-Fi and use your mobile data."],
    PASSWORD_EXPIRED: ["form", "Your password has expired. Change it on your company's Alvoraa website, then sign in here with the new one."],
    SIGN_IN_NOT_ALLOWED: ["form", "Your login cannot be used from here or at this time. Please speak to HR."],
    NO_EMPLOYEE_RECORD: ["form", "Your login is not linked to an employee record, so this app cannot mark attendance for you. Ask HR to link your employee record to your login."],
    EMPLOYEE_NOT_ACTIVE: ["form", "Your employee record is no longer active. Please speak to HR."],
    PASSWORD_SIGNIN_OFF: ["form", "Signing in with an email and password is switched off for your company. Ask HR for a joining code, then press \"I have a joining code\"."],
    APP_OFF_FOR_FIELD: ["form", "Your company has not turned this app on. Keep marking attendance the way you do now. HR can tell you more."],
    FEATURE_OFF: ["form", "This app is not part of your company's plan yet. Please tell HR."],
    APP_TOO_OLD: ["form", "This version of the app is too old. Update it from the app store, then sign in."],
    TOO_MANY_TRIES: ["form", null],   // needs the wait, see below
    OTP_WRONG: ["otp", "That code is not right. Check it and try again."],
    OTP_EXPIRED: ["form", "Your sign-in timed out. Please sign in again."],
    // The phone was signed out because the login's password changed (26 Sep
    // 2026). Shown on the sign-in form the app opens for it.
    PASSWORD_CHANGED_SIGN_IN_AGAIN: ["form", "Your password was changed. Please sign in again."],
    NOTICE_CHANGED: ["form", "The notice changed while you were signing in. Please sign in again."],
    SERVER_ERROR: ["form", "Something went wrong on our side. Please try again in a minute."],
    INVALID_REQUEST: ["form", "Something went wrong. Please try again. If it keeps happening, show this screen to HR."],
  };

  /*
   * Returns { step: "form" | "otp", text, footerCode }. footerCode is always
   * the code itself, so the person can read it out to HR (D11).
   */
  function messageFor(code, values) {
    values = values || {};
    var row = MESSAGES[code];
    var step = row ? row[0] : "form";
    var text = row ? row[1] : null;
    if (code === "ACCOUNT_LOCKED") {
      text = "Too many wrong tries, so your account is locked for now. Wait "
        + waitMinutes(values.retry_after_s) + ", then try again, or reset your password on the website.";
    } else if (code === "TOO_MANY_TRIES") {
      text = "Too many tries from this phone. Wait " + waitMinutes(values.retry_after_s) + ", then try again.";
    } else if (!text) {
      text = "Something went wrong. This app may be out of date. Check for an update, then try again.";
    }
    return { step: step, text: text, footerCode: code };
  }

  /*
   * How an answer looks on the form (ALV-133, 01d §7.1). Red only for wrong
   * details; amber with a lock or a clock for a wait, which is not a mistake;
   * the calm info tone when the person did nothing wrong. Colour is never the
   * only signal: each has its own icon, and the words say it all.
   *   { tone: "error" | "warning" | "info", icon, markPassword }
   * markPassword: the password box is emptied and marked "Type your password
   * again." - only when the password itself may be what was wrong.
   */
  var LOOKS = {
    ACCOUNT_LOCKED: ["warning", "lock"],
    NETWORK_LOCKED: ["warning", "lock"],
    TOO_MANY_TRIES: ["warning", "clock"],
    NO_INTERNET: ["warning", "wifiOff"],
    PASSWORD_SIGNIN_OFF: ["info", "info"],
    PASSWORD_CHANGED_SIGN_IN_AGAIN: ["info", "info"],
    OTP_EXPIRED: ["info", "clock"],
    NOTICE_CHANGED: ["info", "info"],
  };

  function lookFor(code) {
    var look = LOOKS[code] || ["error", "error"];
    return { tone: look[0], icon: look[1], markPassword: code === "SIGN_IN_FAILED" };
  }

  // ── remembering the company code (not a secret, a convenience) ─────────

  var COMPANY_KEY = "alvoraa_company_code";

  function storage(store) {
    if (store) return store;
    try {
      return (typeof localStorage !== "undefined") ? localStorage : null;
    } catch (e) {
      return null;
    }
  }

  function rememberCompany(code, store) {
    var s = storage(store);
    if (!s || typeof code !== "string") return;
    try { s.setItem(COMPANY_KEY, code); } catch (e) { /* fail soft: it is only a convenience */ }
  }

  function rememberedCompany(store) {
    var s = storage(store);
    if (!s) return "";
    try { return s.getItem(COMPANY_KEY) || ""; } catch (e) { return ""; }
  }

  /*
   * The company code back out of the address the phone was using, e.g.
   * the host sargam.alvoraa.co gives "sargam" (also <code>.dev.alvoraa.co).
   * Used when the phone is signed out and the remembered code is missing (a
   * phone that joined with a QR code never typed one). Anything that is not
   * an Alvoraa address gives "" - the person then types the code.
   */
  function companyFromOrigin(origin) {
    var m = /^https:\/\/([a-z0-9-]+)\.(?:dev\.)?alvoraa\.co\/?$/i.exec(
      typeof origin === "string" ? origin.trim() : "");
    return m ? m[1].toLowerCase() : "";
  }

  var api = {
    checkForm: checkForm,
    checkOtp: checkOtp,
    messageFor: messageFor,
    lookFor: lookFor,
    rememberCompany: rememberCompany,
    rememberedCompany: rememberedCompany,
    companyFromOrigin: companyFromOrigin,
    COMPANY_KEY: COMPANY_KEY,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaSigninCore = api;
  }
})(typeof window !== "undefined" ? window : this);
