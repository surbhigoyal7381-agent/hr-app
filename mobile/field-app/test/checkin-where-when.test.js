// Check-in fixes of 27 Sep 2026, found on a real phone on 26 Sep 2026:
//   - the result said "At <workplace>" for a person 13 km away;
//   - the welcome screen said "Check in within 0 m";
//   - the photo time went to the server as UTC with no mark (5 h 30 min early).
// These pin the new words so a merge cannot quietly bring the old ones back.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const screens = require(path.join(__dirname, "..", "web", "js", "checkin-screens.js"));
const { formatDistance, ruleLine, whereLine, localTimeWithOffset, screenFor } = screens;

const WEB = path.join(__dirname, "..", "web", "js");

// ── the result card: where you were ─────────────────────────────────────────

test("inside the radius: names the workplace, the radius and the accuracy", () => {
  const line = whereLine({ workplace: "PPJ Head Office Chandigarh", radius_m: 200,
                           distance_m: 42, within: true, accuracy_m: 14 });
  assert.equal(line, "At PPJ Head Office Chandigarh (within 200 m) · accuracy 14 m");
});

test("no radius (so the check-in was allowed) and far away: the distance, never 'At'", () => {
  const line = whereLine({ workplace: "PPJ Head Office Chandigarh", radius_m: 0,
                           distance_m: 13216, within: null, accuracy_m: 14 });
  assert.equal(line, "About 13.2 km from PPJ Head Office Chandigarh · accuracy 14 m");
});

test("outside a radius that was not enforced: the distance, never 'At'", () => {
  const line = whereLine({ workplace: "Okhla Depot", radius_m: 200,
                           distance_m: 380, within: false, accuracy_m: 9 });
  assert.equal(line, "About 380 m from Okhla Depot · accuracy 9 m");
  assert.doesNotMatch(line, /^At /);
});

test("no workplace: location recorded, with the accuracy", () => {
  const line = whereLine({ workplace: null, radius_m: null, distance_m: null,
                           within: null, accuracy_m: 14 });
  assert.equal(line, "Location recorded · accuracy 14 m");
});

test("a workplace with no distance measured never claims the person was there", () => {
  const line = whereLine({ workplace: "Okhla Depot", radius_m: 0, distance_m: null,
                           within: null, accuracy_m: 20 });
  assert.equal(line, "Location recorded · accuracy 20 m");
});

test("an older server with no location answer: the phone's own accuracy, no workplace claim", () => {
  assert.equal(whereLine(undefined, 13.6), "Location recorded · accuracy 14 m");
  assert.equal(whereLine(undefined, undefined), "Location recorded");
});

test("distances: metres under a kilometre, kilometres with one decimal above", () => {
  assert.equal(formatDistance(0), "0 m");
  assert.equal(formatDistance(740.4), "740 m");
  assert.equal(formatDistance(999), "999 m");
  assert.equal(formatDistance(1000), "1.0 km");
  assert.equal(formatDistance(13216), "13.2 km");
});

test("the refusal outside the radius shows the distance in words a person can read", () => {
  const s = screenFor("OUTSIDE_WORKPLACE",
    { distance_m: 13216, site: "PPJ Head Office Chandigarh", radius_m: 200 }, {});
  assert.equal(s.screen, "outside");
  assert.match(s.body, /about 13\.2 km from PPJ Head Office Chandigarh/);
  assert.match(s.body, /within 200 m/);
  assert.match(s.body, /Nothing has been saved/);
});

test("checkin.js builds the result line from the server's location, not the workplace name", () => {
  const src = fs.readFileSync(path.join(WEB, "checkin.js"), "utf8");
  assert.doesNotMatch(src, /"Where you were · At " \+ state\.workplaceName/);
  assert.match(src, /whereLine\(data\.location, phoneAccuracy\)/);
});

// ── the rule line: radius 0 or none means no limit ─────────────────────────

test("a radius means 'within N m of <workplace>'", () => {
  assert.equal(ruleLine({ name: "PPJ Head Office Chandigarh", radius_m: 200 }),
    "Check in within 200 m of PPJ Head Office Chandigarh");
});

test("radius 0, empty, missing, or no workplace at all: 'from anywhere', never '0 m'", () => {
  for (const wp of [{ name: "X", radius_m: 0 }, { name: "X", radius_m: null },
                    { name: "X", radius_m: "" }, { name: "X" }, null, undefined]) {
    const line = ruleLine(wp);
    assert.equal(line, "Check in from anywhere");
    assert.doesNotMatch(line, /0 m/);
  }
});

test("welcome (join.js and signin.js) and home (checkin.js) all use the shared rule line", () => {
  for (const f of ["join.js", "signin.js", "checkin.js"]) {
    const src = fs.readFileSync(path.join(WEB, f), "utf8");
    assert.match(src, /AlvoraaCheckinScreens\.ruleLine\(/, f);
    assert.doesNotMatch(src, /"Check in within · "/, f);
  }
});

// ── the photo time: local wall clock WITH its offset ─────────────────────────

function fakeDate(y, mo, d, h, mi, s, offsetMinutesEast) {
  return {
    getFullYear: () => y, getMonth: () => mo - 1, getDate: () => d,
    getHours: () => h, getMinutes: () => mi, getSeconds: () => s,
    getTimezoneOffset: () => -offsetMinutesEast,
  };
}

test("an Indian phone sends its own time marked +05:30", () => {
  assert.equal(localTimeWithOffset(fakeDate(2026, 9, 27, 14, 5, 9, 330)),
    "2026-09-27T14:05:09+05:30");
});

test("zones west of UTC and UTC itself are marked too", () => {
  assert.equal(localTimeWithOffset(fakeDate(2026, 1, 2, 3, 4, 5, -300)), "2026-01-02T03:04:05-05:00");
  assert.equal(localTimeWithOffset(fakeDate(2026, 12, 31, 23, 59, 59, 0)), "2026-12-31T23:59:59+00:00");
});

test("a real Date round-trips: the marked time is the same moment", () => {
  const now = new Date(Date.UTC(2026, 8, 27, 8, 35, 9));
  assert.equal(new Date(localTimeWithOffset(now)).getTime(), now.getTime());
});

test("checkin.js no longer sends an unmarked UTC time", () => {
  const src = fs.readFileSync(path.join(WEB, "checkin.js"), "utf8");
  assert.doesNotMatch(src, /captured_at: new Date\(\)\.toISOString\(\)/);
  assert.match(src, /captured_at: window\.AlvoraaCheckinScreens\.localTimeWithOffset\(/);
});
