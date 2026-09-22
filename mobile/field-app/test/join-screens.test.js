// Slice 013, US-37/38: every code the server (or the app itself) can send
// during the join flow lands on a real screen with real words - never a
// blank one, and never matched on English text.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { screenFor, onDateAt, todayOrDateAt } = require(
  path.join(__dirname, "..", "web", "js", "join-screens.js"));

test("QR_EXPIRED reads the exact 01b sentence shape, with the code for HR at the end", () => {
  const r = screenFor("QR_EXPIRED", { expired_at: "2026-09-24 10:05:00" });
  assert.equal(r.screen, "qrExpired");
  assert.equal(r.heading, "This code cannot be used any more");
  assert.match(r.body, /^It ran out on Thursday 24 September at 10:05 am\./);
  assert.deepEqual(r.steps, ["Ask HR for a new code.", "Scan the new code with this app."]);
  assert.equal(r.retry, false);
  assert.equal(r.footerCode, "QR_EXPIRED");
});

test("QR_USED says \"today\" when used_at is today, and the date otherwise", () => {
  const now = new Date("2026-09-17T18:00:00");
  const usedToday = screenFor("QR_USED", { used_at: "2026-09-17 09:01:00" }, { now });
  assert.match(usedToday.body, /^It was already used today at 9:01 am\./);

  const usedEarlier = screenFor("QR_USED", { used_at: "2026-09-10 09:01:00" }, { now });
  assert.match(usedEarlier.body, /^It was already used on Thursday 10 September at 9:01 am\./);
});

test("QR_CANCELLED and QR_NOT_RECOGNISED both land on the dead-code screen shape", () => {
  for (const code of ["QR_CANCELLED", "QR_NOT_RECOGNISED"]) {
    const r = screenFor(code, {});
    assert.equal(r.heading, "This code cannot be used any more");
    assert.equal(r.buttons[0], "Scan a new code");
    assert.equal(r.footerCode, code);
  }
});

test("NOT_FIELD_ROLE names the designation the server actually sent", () => {
  const r = screenFor("NOT_FIELD_ROLE", { designation: "Store Associate" });
  assert.match(r.body, /Store Associate/);
});

test("APP_OFF_FOR_FIELD names the company when given one, and still works without it", () => {
  const withCompany = screenFor("APP_OFF_FOR_FIELD", {}, { company: "Kaveri Transport" });
  assert.match(withCompany.body, /^Kaveri Transport has not turned on/);
  const withoutCompany = screenFor("APP_OFF_FOR_FIELD", {});
  assert.match(withoutCompany.body, /has not turned on/);
});

test("CAMERA_DENIED has its own steps and buttons, not the generic fallback", () => {
  const r = screenFor("CAMERA_DENIED", {});
  assert.equal(r.screen, "camDenied");
  assert.equal(r.steps.length, 3);
  assert.deepEqual(r.buttons, ["Choose a picture instead", "Open phone settings"]);
});

test("the app's own client-made codes (no server call) get real screens too", () => {
  const notAlvoraa = screenFor("QR_NOT_ALVORAA", {});
  assert.equal(notAlvoraa.screen, "notAlvoraa");
  assert.deepEqual(notAlvoraa.buttons, ["Scan again", "Choose a picture instead"]);

  const pickNoQr = screenFor("QR_NOT_FOUND", {});
  assert.equal(pickNoQr.screen, "pickNoQr");

  const noSignal = screenFor("NO_INTERNET", {});
  assert.equal(noSignal.screen, "noSignalJoin");
  assert.equal(noSignal.retry, true);
});

test("TOO_MANY_TRIES and SERVER_ERROR allow Try again; dead codes never do", () => {
  assert.equal(screenFor("TOO_MANY_TRIES", {}).retry, true);
  assert.equal(screenFor("SERVER_ERROR", {}).retry, true);
  assert.equal(screenFor("QR_EXPIRED", {}).retry, false);
  assert.equal(screenFor("QR_USED", {}).retry, false);
  assert.equal(screenFor("QR_CANCELLED", {}).retry, false);
});

// ALV-39 review finding (Major): the wait time was hardcoded at "one minute"
// no matter what the server's real rate-limit window (one hour, field_app_
// limits.py's WINDOW_SECONDS) actually left. The server always sends the
// real number back as values.retry_after_s - the screen must use it.
test("TOO_MANY_TRIES tells the real wait time the server sent, not a hardcoded one", () => {
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 45 }).body, /Wait one minute,/);
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 300 }).body, /Wait 5 minutes,/);
  assert.match(screenFor("TOO_MANY_TRIES", { retry_after_s: 3600 }).body, /Wait about an hour,/);
  // No value at all (a client-made fallback with empty values, e.g. api.js's
  // nginx-level 429) must still say something true, never "NaN" or "0 minutes".
  assert.match(screenFor("TOO_MANY_TRIES", {}).body, /Wait a little while,/);
});

// ALV-39 review finding (Minor): this wording was flagged in its own code
// comment as "unconfirmed against the 008 page" and did not actually match
// it (alvoraa_portal/www/field-checkin.html, FEATURE_OFF.p).
test("FEATURE_OFF matches the real 008 web check-in page byte-for-byte", () => {
  const r = screenFor("FEATURE_OFF", {});
  assert.equal(r.body, "Field check-in is not part of your company's plan yet. Please tell HR.");
});

test("a code this app has never heard of still gets a real screen, with itself as the footer code", () => {
  const r = screenFor("SOME_FUTURE_CODE_2027", { anything: "here" });
  assert.equal(r.screen, "unknownCode");
  assert.equal(r.footerCode, "SOME_FUTURE_CODE_2027");
  assert.ok(r.heading && r.body); // never blank
});

test("onDateAt and todayOrDateAt return empty string rather than throwing on a bad date", () => {
  assert.equal(onDateAt("not-a-date"), "");
  assert.equal(onDateAt(""), "");
  assert.equal(todayOrDateAt(undefined), "");
});
