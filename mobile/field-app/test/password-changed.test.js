// ALV-128, 26 Sep 2026: a password change of any kind signs the phone out and
// asks the person to sign in again - never a block. The server answers
// PASSWORD_CHANGED_SIGN_IN_AGAIN from the punch, the start screen (field_status)
// and the notice; all three lead to the sign-in screen with the company code
// kept and the stored secret forgotten. Run: npm test
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const js = (name) => path.join(__dirname, "..", "web", "js", name);
const { planForGateRefusal, planForConsentRequiredProbe } = require(js("gate-refusal.js"));
const core = require(js("signin-core.js"));

const CODE = "PASSWORD_CHANGED_SIGN_IN_AGAIN";
const HOST = (tenant) => "https:" + "//" + tenant;

test("the gate sends a signed-out phone to sign in again, not to a problem screen", () => {
  assert.deepEqual(planForGateRefusal(CODE, {}), { action: "signInAgain" });
  assert.notEqual(planForGateRefusal(CODE, {}).action, "problem");
  // A block is still a block: the two must never be confused.
  assert.equal(planForGateRefusal("DEVICE_BLOCKED", {}).action, "problem");
});

test("the notice probe hands the code on, and the app treats it the same way", () => {
  const plan = planForConsentRequiredProbe({ ok: false, code: CODE, values: {} });
  assert.deepEqual(plan, { action: "problem", code: CODE, values: {} });
  assert.equal(planForGateRefusal(plan.code, {}).action, "signInAgain");
});

test("the sign-in form says, in plain words, why it opened", () => {
  const msg = core.messageFor(CODE, {});
  assert.equal(msg.step, "form");
  assert.equal(msg.text, "Your password was changed. Please sign in again.");
  assert.equal(msg.footerCode, CODE);
});

test("the company code comes back from the address the phone was using", () => {
  assert.equal(core.companyFromOrigin(HOST("sargam.alvoraa.co")), "sargam");
  assert.equal(core.companyFromOrigin(HOST("sargam.alvoraa.co") + "/"), "sargam");
  assert.equal(core.companyFromOrigin(HOST("Sargam.dev.alvoraa.co")), "sargam");
  for (const bad of [HOST("sargam.alvoraa.co.evil.test"), HOST("evil.test"),
    "http:" + "//sargam.alvoraa.co", "", null, undefined, 42]) {
    assert.equal(core.companyFromOrigin(bad), "", String(bad));
  }
});

// checkin.js is DOM wiring with no module export; these read its source to pin
// that each of the three flows routes the code to the one sign-out path, and
// that the path forgets the stored secret and keeps the company.
const checkin = fs.readFileSync(js("checkin.js"), "utf8");
const signin = fs.readFileSync(js("signin.js"), "utf8");

test("the punch, the start screen and the notice all route to signInAgain", () => {
  const signInAgain = checkin.slice(checkin.indexOf("function signInAgain()"),
    checkin.indexOf("function isSignedOut("));
  assert.match(signInAgain, /forgetPhoneLocally\(\)/, "the stored secret is cleared");
  assert.match(signInAgain, /AlvoraaSignin\.start\(\{/);
  assert.match(signInAgain, /reason: "PASSWORD_CHANGED_SIGN_IN_AGAIN"/);
  assert.match(signInAgain, /previousToken: oldSecret/);
  assert.match(signInAgain, /origin: oldOrigin/);
  // status/home flow (handleGateRefusal), the punch, the notice and its probe
  assert.match(checkin, /plan\.action === "signInAgain"\) \{\s*signInAgain\(\);/);
  assert.equal((checkin.match(/isSignedOut\((result|probePlan)\.code\)/g) || []).length, 3);
});

test("the sign-in keeps the old secret in memory only, and sends it as token", () => {
  assert.equal((signin.match(/token: state\.previousToken \|\| undefined/g) || []).length, 2);
  assert.doesNotMatch(signin, /save\([^)]*previousToken/, "never stored");
  assert.match(signin, /core\.rememberedCompany\(\) \|\| core\.companyFromOrigin\(opts\.origin\)/);
});
