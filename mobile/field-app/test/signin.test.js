// ALV-128: signing in with a work email and password. The company code only
// ever becomes an Alvoraa address; a bad form is refused before any call;
// every server answer has plain words and the code for HR; the password is
// never kept. Run: npm test
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const hostCheck = require(path.join(__dirname, "..", "web", "js", "host-check.js"));
const core = require(path.join(__dirname, "..", "web", "js", "signin-core.js"));
const { signInWithPassword, confirmSignInCode } = require(
  path.join(__dirname, "..", "web", "js", "api.js"));

const { originForCompanyCode } = hostCheck;
const HOST = (tenant) => "https:" + "//" + tenant + ".alvoraa.co";

// ── the company code ──────────────────────────────────────────────────────

test("a plain company code becomes that tenant's address in every build", () => {
  for (const build of ["debug", "pilot", "release"]) {
    assert.deepEqual(originForCompanyCode("sargam", build),
      { ok: true, origin: HOST("sargam"), code: "sargam" });
  }
});

test("what people paste is cleaned first", () => {
  for (const typed of ["  Sargam ", "SARGAM", "sargam.alvoraa.co", HOST("sargam"), HOST("sargam") + "/"]) {
    assert.equal(originForCompanyCode(typed, "release").origin, HOST("sargam"), typed);
  }
});

test("the dev site is allowed in pilot and debug builds only", () => {
  assert.equal(originForCompanyCode("sargam.dev", "pilot").origin, HOST("sargam.dev"));
  assert.equal(originForCompanyCode("sargam.dev", "debug").origin, HOST("sargam.dev"));
  assert.deepEqual(originForCompanyCode("sargam.dev", "release"),
    { ok: false, code: "COMPANY_CODE_INVALID" });
});

test("nothing typed can point the app at another server", () => {
  const hostile = [
    "", "   ", "evil.com", "sargam.evil", "a.b.c", "sargam/../x", "sargam@evil.com",
    "sargam:8443", "xn--pj-8ka", "sarg am", "-sargam", "sargam-", "sargam.qa",
    "javascript:alert(1)", "http" + "://sargam.alvoraa.co.evil.com", "ppј", // Cyrillic j
    "x".repeat(101), 42, null, undefined,
  ];
  for (const typed of hostile) {
    assert.deepEqual(originForCompanyCode(typed, "debug"),
      { ok: false, code: "COMPANY_CODE_INVALID" }, String(typed));
  }
});

test("the QR link and the company code share one host rule", () => {
  assert.equal(hostCheck.hostIsAllowed("sargam.alvoraa.co", "release"), true);
  assert.equal(hostCheck.hostIsAllowed("sargam.dev.alvoraa.co", "release"), false);
  assert.equal(hostCheck.hostIsAllowed("sargam.dev.alvoraa.co", "pilot"), true);
  assert.equal(hostCheck.hostIsAllowed("alvoraa.co", "debug"), false);
  assert.equal(hostCheck.hostIsAllowed("sargam.alvoraa.co", "nightly"), false);
});

// ── the form, before any call ─────────────────────────────────────────────

test("a filled-in form is ready to send, with the cleaned company and email", () => {
  const out = core.checkForm(" Sargam ", " ravi@example.com ", "secret", "release", hostCheck);
  assert.deepEqual(out, { ok: true, origin: HOST("sargam"), companyCode: "sargam", email: "ravi@example.com" });
});

test("each empty or bad box is named, company first", () => {
  assert.deepEqual(core.checkForm("", "ravi@example.com", "x", "release", hostCheck),
    { ok: false, code: "COMPANY_CODE_INVALID", field: "company" });
  assert.deepEqual(core.checkForm("sargam", "ravi", "x", "release", hostCheck),
    { ok: false, code: "EMAIL_INVALID", field: "email" });
  assert.deepEqual(core.checkForm("sargam", "", "x", "release", hostCheck),
    { ok: false, code: "EMAIL_INVALID", field: "email" });
  assert.deepEqual(core.checkForm("sargam", "ravi@example.com", "", "release", hostCheck),
    { ok: false, code: "PASSWORD_MISSING", field: "password" });
  assert.equal(core.checkForm("sargam", "ravi@example.com", "x".repeat(513), "release", hostCheck).code,
    "PASSWORD_MISSING");
});

test("the one-time code is cleaned of spaces and must be there", () => {
  assert.deepEqual(core.checkOtp(" 123 456 "), { ok: true, otp: "123456" });
  assert.equal(core.checkOtp("").code, "OTP_MISSING");
  assert.equal(core.checkOtp("1".repeat(13)).code, "OTP_MISSING");
});

// ── what each answer says ─────────────────────────────────────────────────

const SERVER_CODES = ["SIGN_IN_FAILED", "ACCOUNT_LOCKED", "PASSWORD_EXPIRED", "SIGN_IN_NOT_ALLOWED",
  "OTP_WRONG", "OTP_EXPIRED", "NO_EMPLOYEE_RECORD", "EMPLOYEE_NOT_ACTIVE", "PASSWORD_SIGNIN_OFF",
  "APP_OFF_FOR_FIELD", "FEATURE_OFF", "APP_TOO_OLD", "TOO_MANY_TRIES", "SERVER_ERROR",
  "INVALID_REQUEST", "NO_INTERNET", "NOTICE_CHANGED", "NETWORK_LOCKED"];

test("every sign-in answer has its own plain sentence and the code for HR", () => {
  const generic = core.messageFor("SOMETHING_NEW", {}).text;
  for (const code of SERVER_CODES) {
    const msg = core.messageFor(code, { retry_after_s: 300 });
    assert.ok(msg.text && msg.text.length > 20, code);
    assert.notEqual(msg.text, generic, `${code} fell through to the unknown-code sentence`);
    assert.equal(msg.footerCode, code);
    assert.ok(["form", "otp"].includes(msg.step), code);
  }
});

test("a wrong code stays on the code step; a timed-out one goes back to the form", () => {
  assert.equal(core.messageFor("OTP_WRONG").step, "otp");
  assert.equal(core.messageFor("OTP_EXPIRED").step, "form");
  assert.equal(core.messageFor("SIGN_IN_FAILED").step, "form");
});

test("the lock and the limit say how long to wait", () => {
  assert.match(core.messageFor("ACCOUNT_LOCKED", { retry_after_s: 300 }).text, /5 minutes/);
  assert.match(core.messageFor("TOO_MANY_TRIES", { retry_after_s: 3600 }).text, /60 minutes/);
  assert.match(core.messageFor("ACCOUNT_LOCKED", {}).text, /a few minutes/);
});

test("a locked network is never called a locked account (review fix)", () => {
  const text = core.messageFor("NETWORK_LOCKED", { retry_after_s: 300 }).text;
  // Security's words, 27 Sep 2026 (D-M3-6): the per-network lock lasts
  // minutes, and mobile data is another network.
  assert.equal(text, "Too many wrong sign-in attempts from this network. Try again in a few minutes, "
    + "or turn off Wi-Fi and use your mobile data.");
  assert.doesNotMatch(text, /account/i);
});

test("a phone whose login was unlinked is asked to sign in again (SEC-28)", () => {
  const screens = require(path.join(__dirname, "..", "web", "js", "checkin-screens.js"));
  const info = screens.screenFor("LOGIN_UNLINKED", {}, { company: "Sargam Metals" });
  assert.equal(info.heading, "Please sign in again");
  assert.match(info.body, /no longer linked/);
});

test("joining codes switched off has its own screen with a way to sign in (ALV-128)", () => {
  const joinScreens = require(path.join(__dirname, "..", "web", "js", "join-screens.js"));
  const info = joinScreens.screenFor("JOIN_CODE_OFF", {});
  assert.equal(info.screen, "codeJoinOff");
  assert.equal(info.body,
    "Joining codes are switched off at your company. Sign in with your work email and password, or ask HR.");
  assert.equal(info.buttons[0], "Sign in with email and password");
  assert.equal(info.footerCode, "JOIN_CODE_OFF");
});

test("an unknown code still gets words, never a blank screen", () => {
  const msg = core.messageFor("SOMETHING_NEW", {});
  assert.ok(msg.text);
  assert.equal(msg.footerCode, "SOMETHING_NEW");
});

// ── what is kept ──────────────────────────────────────────────────────────

function fakeStore() {
  const data = {};
  return {
    data,
    setItem: (k, v) => { data[k] = String(v); },
    getItem: (k) => (k in data ? data[k] : null),
  };
}

test("only the company code is remembered, never an email or a password", () => {
  const store = fakeStore();
  core.rememberCompany("sargam", store);
  assert.equal(core.rememberedCompany(store), "sargam");
  assert.deepEqual(Object.keys(store.data), [core.COMPANY_KEY]);
});

test("a storage that throws is shrugged off", () => {
  const broken = { setItem() { throw new Error("blocked"); }, getItem() { throw new Error("blocked"); } };
  core.rememberCompany("sargam", broken);
  assert.equal(core.rememberedCompany(broken), "");
});

// ── the two calls ─────────────────────────────────────────────────────────

function fakeFetch(bodyObj) {
  const f = (url, init) => {
    f.url = url;
    f.init = init;
    return Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(bodyObj)) });
  };
  return f;
}

test("sign in posts to the sign-in method, with agreed=0 and the password in the body only", async () => {
  const fetchImpl = fakeFetch({ message: { status: "not_agreed", token: "t" } });
  const out = await signInWithPassword(HOST("sargam"),
    { email: "ravi@example.com", password: "secret", device_label: "", platform: "android" },
    { fetchImpl, appVersion: "0.2.0" });
  assert.deepEqual(out, { ok: true, data: { status: "not_agreed", token: "t" } });
  assert.equal(fetchImpl.url, HOST("sargam") + "/api/method/alvoraa_portal.field_app_join.sign_in_with_password");
  assert.equal(fetchImpl.init.method, "POST");
  assert.ok(!fetchImpl.url.includes("secret"), "the password is never in the address");
  assert.deepEqual(JSON.parse(fetchImpl.init.body),
    { email: "ravi@example.com", password: "secret", device_label: "", platform: "android", agreed: 0 });
});

test("the code step posts the one-time id and code, and never a password", async () => {
  const fetchImpl = fakeFetch({ message: { status: "active", token: "t" } });
  await confirmSignInCode(HOST("sargam"), { tmp_id: "abc", otp: "123456", device_label: "", platform: "android" },
    { fetchImpl });
  assert.equal(fetchImpl.url, HOST("sargam") + "/api/method/alvoraa_portal.field_app_join.confirm_sign_in_code");
  const body = JSON.parse(fetchImpl.init.body);
  assert.equal(body.tmp_id, "abc");
  assert.equal(body.otp, "123456");
  assert.ok(!("password" in body));
});

test("a refusal comes back as its code", async () => {
  const fetchImpl = (url, init) => Promise.resolve({
    ok: false, status: 401,
    text: () => Promise.resolve(JSON.stringify({ exc_type: "AuthenticationError", code: "SIGN_IN_FAILED", values: {} })),
  });
  const out = await signInWithPassword(HOST("sargam"), { email: "a@example.com", password: "x" }, { fetchImpl });
  assert.deepEqual(out, { code: "SIGN_IN_FAILED", values: {} });
});
