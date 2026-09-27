// Slice 013, AC-172 (SEC-14, OPS-55): only real tenant links are accepted, and
// a refused link never causes a network call. Run: npm test
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { checkEnrolLink } = require("../web/js/host-check.js");

const CODE = "A".repeat(20) + "b_-9".repeat(5) + "xyz"; // 43 URL-safe characters
assert.equal(CODE.length, 43);

const HOSTILE = [
  ["plain http", `http://ppj.alvoraa.co/enrol#t=${CODE}`],
  ["look-alike domain", `https://evilalvoraa.co/enrol#t=${CODE}`],
  ["our name inside another domain", `https://alvoraa.co.evil.com/enrol#t=${CODE}`],
  ["user part pointing elsewhere", `https://x.alvoraa.co@evil.com/enrol#t=${CODE}`],
  ["user and password", `https://a:b@ppj.alvoraa.co/enrol#t=${CODE}`],
  ["a port", `https://x.alvoraa.co:8443/enrol#t=${CODE}`],
  ["the bare domain", `https://alvoraa.co/enrol#t=${CODE}`],
  ["three labels", `https://a.b.c.alvoraa.co/enrol#t=${CODE}`],
  ["two labels, not dev", `https://a.b.alvoraa.co/enrol#t=${CODE}`],
  ["punycode label", `https://xn--pj-8ka.alvoraa.co/enrol#t=${CODE}`],
  ["unicode label (becomes punycode)", `https://ppј.alvoraa.co/enrol#t=${CODE}`],
  ["code too short", `https://ppj.alvoraa.co/enrol#t=${CODE.slice(1)}`],
  ["code too long", `https://ppj.alvoraa.co/enrol#t=${CODE}A`],
  ["code with a bad character", `https://ppj.alvoraa.co/enrol#t=${CODE.slice(1)}!`],
  ["code in the query, not the fragment", `https://ppj.alvoraa.co/enrol?t=${CODE}`],
  ["query and fragment", `https://ppj.alvoraa.co/enrol?x=1#t=${CODE}`],
  ["other path", `https://ppj.alvoraa.co/login#t=${CODE}`],
  ["path trick with a backslash", `https://ppj.alvoraa.co\\@evil.com/enrol#t=${CODE}`],
  ["trailing dot host", `https://ppj.alvoraa.co./enrol#t=${CODE}`],
  ["javascript scheme", `javascript:alert(1)//ppj.alvoraa.co/enrol#t=${CODE}`],
  ["a UPI payment code", "upi://pay?pa=someone@okbank&pn=Shop&am=10"],
  ["spaces around it", ` https://ppj.alvoraa.co/enrol#t=${CODE}`],
  ["not text", 12345],
  ["empty", ""],
  ["fragment without t=", `https://ppj.alvoraa.co/enrol#${CODE}`],
  ["label ending in a hyphen", `https://ppj-.alvoraa.co/enrol#t=${CODE}`],
];

test("every hostile link is refused with QR_NOT_ALVORAA and no network call", () => {
  assert.ok(HOSTILE.length >= 15, "AC-172 needs at least 15 cases");
  const realFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = () => { calls += 1; throw new Error("no network allowed"); };
  try {
    for (const buildType of ["debug", "pilot", "release"]) {
      for (const [why, link] of HOSTILE) {
        assert.deepEqual(checkEnrolLink(link, buildType), { ok: false, code: "QR_NOT_ALVORAA" },
          `${why} should be refused in ${buildType}`);
      }
    }
  } finally {
    globalThis.fetch = realFetch;
  }
  assert.equal(calls, 0);
});

test("a tenant link passes in every build type, host kept and code returned", () => {
  for (const buildType of ["debug", "pilot", "release"]) {
    assert.deepEqual(checkEnrolLink(`https://ppj.alvoraa.co/enrol#t=${CODE}`, buildType),
      { ok: true, origin: "https://ppj.alvoraa.co", code: CODE });
  }
});

test("upper-case host letters are fine after parsing", () => {
  assert.equal(checkEnrolLink(`https://PPJ.Alvoraa.CO/enrol#t=${CODE}`, "release").origin,
    "https://ppj.alvoraa.co");
});

test("a dev tenant link passes in pilot and debug builds, never in release", () => {
  const link = `https://ppj.dev.alvoraa.co/enrol#t=${CODE}`;
  assert.equal(checkEnrolLink(link, "pilot").ok, true);
  assert.equal(checkEnrolLink(link, "debug").ok, true);
  assert.deepEqual(checkEnrolLink(link, "release"), { ok: false, code: "QR_NOT_ALVORAA" });
});

test("an unknown build type refuses everything", () => {
  assert.equal(checkEnrolLink(`https://ppj.alvoraa.co/enrol#t=${CODE}`, "prod").ok, false);
  assert.equal(checkEnrolLink(`https://ppj.alvoraa.co/enrol#t=${CODE}`, undefined).ok, false);
});
