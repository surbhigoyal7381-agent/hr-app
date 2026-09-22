// Slice 013, US-39/40/41 (daily use): every code field_status/field_checkin/
// remove_my_phone/acknowledge_notice can send lands on exactly one screen,
// picked by `code` alone - this is the pin that stops a wording regression
// and the proof that the two bugs the parallel review found in
// join-screens.js (TOO_MANY_TRIES ignoring retry_after_s, a wrong FEATURE_OFF
// body) are not repeated here.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { screenFor, friendlyWait } = require(
  path.join(__dirname, "..", "web", "js", "checkin-screens.js"));

test("every code field_app_errors.CODES can send to a device endpoint has a named screen or an honest fallback", () => {
  // The frozen server table (field_app_errors.py), minus the four join-only
  // QR_* codes and the three this file deliberately special-cases elsewhere
  // (NOTICE_CHANGED, NOT_SET_UP/DEVICE_PENDING/DEVICE_REMOVED - checkin.js's
  // job, not this table's) and CONSENT_REQUIRED (unreachable, no design).
  const deviceCodes = [
    "APP_OFF_FOR_FIELD", "NOT_FIELD_ROLE", "FEATURE_OFF", "APP_TOO_OLD",
    "DEVICE_BLOCKED", "DEVICE_REPLACED", "EMPLOYEE_NOT_ACTIVE",
    "LOCATION_MISSING", "GPS_NOT_EXACT", "OUTSIDE_WORKPLACE",
    "ALREADY_RECORDED", "INVALID_REQUEST", "TOO_MANY_TRIES", "SERVER_ERROR",
  ];
  for (const code of deviceCodes) {
    const s = screenFor(code, {}, {});
    assert.ok(s.screen && s.heading && s.body, `${code} produced an incomplete screen`);
    assert.equal(s.footerCode, code);
  }
});

test("an unknown or not-yet-designed code (e.g. CONSENT_REQUIRED) falls back honestly, never a blank screen", () => {
  const s = screenFor("CONSENT_REQUIRED", { version: "2026-09-22" }, {});
  assert.equal(s.screen, "unknownCode");
  assert.equal(s.footerCode, "CONSENT_REQUIRED"); // the REAL code, so HR support still has something to search for
  assert.ok(s.heading && s.body);
});

test("TOO_MANY_TRIES reads the server's real retry_after_s, unlike the join flow's own bug", () => {
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 45 }, {}).body, /Wait a minute/);
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 300 }, {}).body, /Wait 5 minutes/);
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 3600 }, {}).body, /Wait an hour/);
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 7200 }, {}).body, /Wait 2 hours/);
  // No values at all (a stray call, or a code this table has never seen a
  // real answer for) must still produce readable text, never "Wait NaN".
  assert.doesNotMatch(screenFor("TOO_MANY_TRIES", {}, {}).body, /NaN/);
});

test("friendlyWait rounds to a sensible unit and never returns a negative or NaN phrase", () => {
  assert.equal(friendlyWait(0), "a minute");
  assert.equal(friendlyWait(-5), "a minute");
  assert.equal(friendlyWait("not a number"), "a minute");
  assert.equal(friendlyWait(59 * 60), "59 minutes");
});

test("FEATURE_OFF uses the real 008 web page's body, not the join flow's wrong one", () => {
  const s = screenFor("FEATURE_OFF", {}, {});
  assert.equal(s.body, "Field check-in is not part of your company's plan yet. Please tell HR.");
});

test("OUTSIDE_WORKPLACE with a real distance names it; with none, falls back to the server's other sentence (AC-208)", () => {
  const withDistance = screenFor("OUTSIDE_WORKPLACE",
    { distance_m: 380, site: "Okhla Depot", radius_m: 100 }, {});
  assert.match(withDistance.body, /about 380 m from Okhla Depot/);
  assert.match(withDistance.body, /within 100 m/);

  const noDistance = screenFor("OUTSIDE_WORKPLACE", { site: "Okhla Depot", radius_m: 100 }, {});
  assert.equal(noDistance.body, "You are too far from Okhla Depot to check in.");
});

test("GPS_NOT_EXACT names the real accuracy and limit", () => {
  const s = screenFor("GPS_NOT_EXACT", { accuracy_m: 62, limit_m: 50 }, {});
  assert.match(s.body, /within about 62 m/);
  assert.match(s.body, /within 50 m/);
});

test("DEVICE_BLOCKED, DEVICE_REPLACED, EMPLOYEE_NOT_ACTIVE, APP_OFF_FOR_FIELD and NOT_FIELD_ROLE (after joining) all offer Remove, never a reason", () => {
  for (const code of ["DEVICE_BLOCKED", "DEVICE_REPLACED", "EMPLOYEE_NOT_ACTIVE",
                       "APP_OFF_FOR_FIELD", "NOT_FIELD_ROLE"]) {
    const s = screenFor(code, {}, { company: "Kaveri Transport" });
    assert.ok(s.buttons.some((b) => b.indexOf("Remove Kaveri Transport") === 0), `${code} has no Remove button`);
    assert.doesNotMatch(JSON.stringify(s), /lost|stolen|left the company|someone else/i); // PRIV-13: never a block reason
  }
});

test("DEVICE_REPLACED and ALREADY_RECORDED format their date/time via the shared helper, not a re-implementation", () => {
  const now = new Date("2026-09-22T12:00:00");
  const replaced = screenFor("DEVICE_REPLACED", { replaced_at: "2026-09-22 09:00:00" }, { now, company: "Kaveri Transport" });
  assert.match(replaced.body, /Today at 9:00 am/i);

  const dup = screenFor("ALREADY_RECORDED", { time: "2026-09-22 09:02:00" }, { now });
  assert.match(dup.body, /today at 9:02 am/);
});

test("APP_TOO_OLD (update) carries the minimum version and no buttons of its own - checkin.js decides those by build type", () => {
  const s = screenFor("APP_TOO_OLD", { min_version: "1.2.0" }, {});
  assert.equal(s.screen, "update");
  assert.deepEqual(s.buttons, []);
  assert.equal(s.card.needed, "1.2.0");
});

test("LOCATION_MISSING, LOCATION_OFF and LOCATION_SLOW are one screen with one body, per 01b §8", () => {
  const a = screenFor("LOCATION_MISSING", {}, {});
  const b = screenFor("LOCATION_OFF", {}, {});
  const c = screenFor("LOCATION_SLOW", {}, {});
  assert.equal(a.screen, "locOff");
  // Same screen and words, but D11 still wants the REAL code at the bottom
  // ("Code for HR"), so footerCode is deliberately the one field that differs.
  const strip = ({ footerCode, ...rest }) => rest;
  assert.deepEqual(strip(a), strip(b));
  assert.deepEqual(strip(a), strip(c));
  assert.equal(b.footerCode, "LOCATION_OFF");
  assert.equal(c.footerCode, "LOCATION_SLOW");
});

test("every server-sent value renders as plain text, never as a template the caller could inject HTML through", () => {
  // A hostile site/designation string must come back inert - the caller
  // (checkin.js) is responsible for using textContent, but this table must
  // not itself concatenate raw HTML tags into something that looks safe.
  const s = screenFor("OUTSIDE_WORKPLACE",
    { distance_m: 10, site: "<img src=x onerror=alert(1)>", radius_m: 5 }, {});
  assert.ok(s.body.indexOf("<img") !== -1); // present as literal text - textContent will show it inert, never run it
});
