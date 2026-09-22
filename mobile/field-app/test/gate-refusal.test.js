// Regression test for 05-review-daily-use.md's M2: a phone in
// "Consent not given" (server code CONSENT_REQUIRED) must recover through
// the notice-again screen, the same way NOTICE_CHANGED already does - not
// fall through to the generic "something's wrong, check for an update" loop
// with no way out.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { planForGateRefusal, planForConsentRequiredProbe } = require(
  path.join(__dirname, "..", "web", "js", "gate-refusal.js"));

test("NOT_SET_UP, DEVICE_PENDING and DEVICE_REMOVED all forget the phone locally and return to first launch", () => {
  for (const code of ["NOT_SET_UP", "DEVICE_PENDING", "DEVICE_REMOVED"]) {
    assert.deepEqual(planForGateRefusal(code, {}), { action: "forgetAndFirst" });
  }
});

test("NOTICE_CHANGED goes straight to the notice-again screen with its own values", () => {
  const values = { version: "2026-09-22", rows: [{ heading: "h", body: "b" }], retention_days: 90, what_changed: "x" };
  assert.deepEqual(planForGateRefusal("NOTICE_CHANGED", values), { action: "noticeAgain", values });
});

test("CONSENT_REQUIRED does NOT fall through to a generic problem screen - this is the M2 bug itself", () => {
  const plan = planForGateRefusal("CONSENT_REQUIRED", { version: "2026-09-22" });
  assert.equal(plan.action, "probeConsentRequired");
  assert.notEqual(plan.action, "problem"); // the exact regression: it used to end up here
});

test("every other code (blocked, replaced, left, appOff, notField, featureOff, tooMany, serverError, an unknown code) is a plain problem screen", () => {
  for (const code of ["DEVICE_BLOCKED", "DEVICE_REPLACED", "EMPLOYEE_NOT_ACTIVE",
                       "APP_OFF_FOR_FIELD", "NOT_FIELD_ROLE", "FEATURE_OFF",
                       "TOO_MANY_TRIES", "SERVER_ERROR", "SOMETHING_THIS_FILE_HAS_NEVER_SEEN"]) {
    const plan = planForGateRefusal(code, { a: 1 });
    assert.deepEqual(plan, { action: "problem", code, values: { a: 1 } });
  }
});

test("the CONSENT_REQUIRED probe: a NOTICE_CHANGED answer (the expected, real-world case) shows the notice again", () => {
  const values = { version: "2026-09-22", rows: [{ heading: "h", body: "b" }], retention_days: 90, what_changed: "x" };
  const plan = planForConsentRequiredProbe({ ok: false, code: "NOTICE_CHANGED", values });
  assert.deepEqual(plan, { action: "noticeAgain", values });
});

test("the CONSENT_REQUIRED probe: any other refusal (the employee left, the app is off, no internet) is shown plainly, not swallowed", () => {
  for (const code of ["EMPLOYEE_NOT_ACTIVE", "APP_OFF_FOR_FIELD", "NO_INTERNET", "SERVER_ERROR"]) {
    const plan = planForConsentRequiredProbe({ ok: false, code, values: { z: 9 } });
    assert.deepEqual(plan, { action: "problem", code, values: { z: 9 } });
  }
});

test("the CONSENT_REQUIRED probe: an outright ok answer (never happens with a real server) reloads status rather than crashing", () => {
  const plan = planForConsentRequiredProbe({ ok: true, data: {} });
  assert.deepEqual(plan, { action: "reloadStatus" });
});

test("planForGateRefusal never mutates the values object it was given", () => {
  const values = Object.freeze({ version: "2026-09-22" });
  assert.doesNotThrow(() => planForGateRefusal("CONSENT_REQUIRED", values));
  assert.doesNotThrow(() => planForGateRefusal("NOTICE_CHANGED", values));
});
